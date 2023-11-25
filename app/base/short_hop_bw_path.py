from distutils.command.build_scripts import first_line_re
from operator import attrgetter
from sys import path_hooks
from tempfile import tempdir
from time import sleep
from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.lib.packet import packet,ethernet
from ryu.topology import event
from ryu.topology.api import get_switch,get_link,get_all_link
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

import networkx as nx

class MyShortestForwarding(app_manager.RyuApp):
    '''
    class to achive shortest path to forward, based on minimum hop count
    '''
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self,*args,**kwargs):
        super(MyShortestForwarding,self).__init__(*args,**kwargs)

        #set data structor for topo construction
        self.network = nx.DiGraph()        #store the dj graph
        self.paths = {}        #store the shortest path
        self.topology_api_app = self
        self.datapaths = {}
        self.bw = {} #bw[dpid][port][r,t,remain->n]
        self.monitor_thread = hub.spawn(self._monitor)
        self.bw_m = {
            1:{1: 10,2: 10,3: 5,4: 5, 5:10},
            2:{1: 10,2: 3},
            3:{1: 5,2: 3,3: 3},
            4:{1: 3,2: 5},
            5:{1: 5,2: 3,3: 3,4: 8},
            6:{1: 3,2: 3,3: 2,4: 8},
            7:{1: 5,2: 3,3: 5},
            8:{1: 2,2: 8,3: 4,4: 5},
            9:{1: 5,2: 5,3: 8,4: 10}
                    }

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        '''
        manage the initial link between switch and controller
        '''
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = ofp_parser.OFPMatch()    #for all packet first arrive, match it successful, send it ro controller
        actions  = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath, 0, match, actions)

    def add_flow(self,datapath,priority,match,actions):
        '''
        fulfil the function to add flow entry to switch
        '''
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]

        mod = ofp_parser.OFPFlowMod(datapath=datapath,priority=priority,match=match,instructions=inst)

        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,ev):
        # get topo info
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        in_port = msg.match['in_port']

        # get outport
        out_port = self.get_out_port(datapath,eth_pkt.src,eth_pkt.dst,in_port)
        actions = [ofp_parser.OFPActionOutput(out_port)]

        # install flow entry
        if out_port != ofproto.OFPP_FLOOD:
            match = ofp_parser.OFPMatch(in_port=in_port,eth_dst=eth_pkt.dst)
            self.add_flow(datapath,1,match,actions)

        # send packet_out msg to datapath
        out = ofp_parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions
            )

        datapath.send_msg(out)

    #get topology and store it into networkx object
    @set_ev_cls(event.EventSwitchEnter,[CONFIG_DISPATCHER,MAIN_DISPATCHER])    #event is not from openflow protocol, is come from switchs` state changed, just like: link to controller at the first time or send packet to controller
    def get_topology(self,ev):
        #store nodes info into the Graph
        switch_list = get_switch(self.topology_api_app,None)    #------------need to get info,by debug
        switches = [switch.dp.id for switch in switch_list]
        self.network.add_nodes_from(switches)

        #store links info into the Graph
        link_list = get_all_link(self.topology_api_app)
        #port_no, in_port    ---------------need to debug, get diffirent from  both
        links = [(link.src.dpid,link.dst.dpid,{'port':link.src.port_no}) for link in link_list]    #add edge, need src,dst,weigtht
        self.network.add_edges_from(links)

        links = [(link.dst.dpid,link.src.dpid,{'port':link.dst.port_no}) for link in link_list]
        self.network.add_edges_from(links)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        for stat in sorted(body, key=attrgetter('port_no')):
            dpid=ev.msg.datapath.id
            self.bw.setdefault(dpid, {})
            self.bw[dpid].setdefault(stat.port_no, {})
            if 'n' not in self.bw[dpid][stat.port_no]:
                self.bw[dpid][stat.port_no]['r']=0
                self.bw[dpid][stat.port_no]['t']=0
                self.bw[dpid][stat.port_no]['n']=0
            rx=stat.rx_bytes-self.bw[dpid][stat.port_no]['r']
            tx=stat.tx_bytes-self.bw[dpid][stat.port_no]['t']

            tmp_bw=(rx+tx)*8/1048576
            if dpid in self.bw_m and stat.port_no in self.bw_m[dpid]:
                self.bw[dpid][stat.port_no]['n']=self.bw_m[dpid][stat.port_no]-tmp_bw

            self.bw[dpid][stat.port_no]['r'] = stat.rx_bytes
            self.bw[dpid][stat.port_no]['t'] = stat.tx_bytes

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(1)

    def _request_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)


    def get_best_path(self,src,dst):
        all_path=nx.all_shortest_paths(self.network,src,dst)
        tmp_path=[]
        tmp_bw=0
        for path in all_path:
            t_bw=2047483647
            print(path)
            for i in range(2,len(path)):
                out_port = self.network[path[i-1]][path[i]]['port']
                if path[i-1] in self.bw and out_port in self.bw[path[i-1]]:
                    t_bw=min(t_bw, self.bw[path[i-1]][out_port]['n'])
            if t_bw > tmp_bw:
                tmp_bw=t_bw
                tmp_path=path
        return tmp_path

    def get_out_port(self,datapath,src,dst,in_port):
        dpid = datapath.id

        #the first :Doesn`t find src host at graph
        if src not in self.network:
            self.network.add_node(src)
            self.network.add_edge(dpid, src, {'port':in_port})
            self.network.add_edge(src, dpid)
            self.paths.setdefault(src, {})

        #second: search the shortest path, from src to dst host
        if dst in self.network:
            if dst not in self.paths[src]:    #if not cache src to dst path,then to find it
                path = self.get_best_path(src,dst)
                self.paths[src][dst]=path
            path = self.paths[src][dst]
            next_hop = path[path.index(dpid)+1]
            print(path)
            #print("1ooooooooooooooooooo")
            #print(self.network[dpid][next_hop])
            out_port = self.network[dpid][next_hop]['port']
            print("path: ", path)

        else:
            out_port = datapath.ofproto.OFPP_FLOOD    #By flood, to find dst, when dst get packet, dst will send a new back,the graph will record dst info
            #print("8888888888 not find dst")
        return out_port
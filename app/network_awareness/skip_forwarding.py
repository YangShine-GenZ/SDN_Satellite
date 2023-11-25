from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.lib.packet import packet,ethernet
from ryu.topology import event
from ryu.topology.api import get_switch,get_link
from ryu.ofproto import ofproto_v1_3

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

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        '''
        manage the initial link between switch and controller
        '''
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = ofp_parser.OFPMatch()    #for all packet first arrive, match it successful, send it ro controller
        actions  = [ofp_parser.OFPActionOutput(
                            ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER
                            )]

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
        '''
        manage the packet which comes from switch
        '''
        #first get event infomation
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        in_port = msg.match['in_port']
        dpid = datapath.id

        #second get ethernet protocol message
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)

        eth_src = eth_pkt.src     #note: mac info willn`t  change in network
        eth_dst = eth_pkt.dst

        out_port = self.get_out_port(datapath,eth_src,eth_dst,in_port)
        actions = [ofp_parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = ofp_parser.OFPMatch(in_port=in_port,eth_dst=eth_dst)
            self.add_flow(datapath,1,match,actions)

        out = ofp_parser.OFPPacketOut(
                datapath=datapath,buffer_id=msg.buffer_id,in_port=in_port,
                actions=actions,data=msg.data
            )

        datapath.send_msg(out)

    @set_ev_cls(event.EventSwitchEnter,[CONFIG_DISPATCHER,MAIN_DISPATCHER])    #event is not from openflow protocol, is come from switchs` state changed, just like: link to controller at the first time or send packet to controller
    def get_topology(self,ev):
        '''
        get network topo construction, save info in the dict
        '''

        #store nodes info into the Graph
        switch_list = get_switch(self.topology_api_app,None)    #------------need to get info,by debug
        switches = [switch.dp.id for switch in switch_list]
        self.network.add_nodes_from(switches)

        #store links info into the Graph
        link_list = get_link(self.topology_api_app,None)
        #port_no, in_port    ---------------need to debug, get diffirent from  both
        links = [(link.src.dpid,link.dst.dpid,{'attr_dict':{'port':link.dst.port_no}}) for link in link_list]    #add edge, need src,dst,weigtht
        self.network.add_edges_from(links)

        links  = [(link.dst.dpid,link.src.dpid,{'attr_dict':{'port':link.dst.port_no}}) for link in link_list]
        self.network.add_edges_from(links)

    def get_out_port(self,datapath,src,dst,in_port):
        '''
        datapath: is current datapath info
        src,dst: both are the host info
        in_port: is current datapath in_port
        '''
        dpid = datapath.id

        #the first :Doesn`t find src host at graph
        if src not in self.network:
            self.network.add_node(src)
            self.network.add_edge(dpid, src, attr_dict={'port':in_port})
            self.network.add_edge(src, dpid)
            self.paths.setdefault(src, {})

        #second: search the shortest path, from src to dst host
        if dst in self.network:
            if dst not in self.paths[src]:    #if not cache src to dst path,then to find it
                path = nx.shortest_path(self.network,src,dst)
                self.paths[src][dst]=path

            path = self.paths[src][dst]
            next_hop = path[path.index(dpid)+1]
            #print("1ooooooooooooooooooo")
            #print(self.network[dpid][next_hop])
            out_port = self.network[dpid][next_hop]['attr_dict']['port']
            #print("2ooooooooooooooooooo")
            #print(out_port)

            #get path info
            #print("6666666666 find dst")
            print(path)
        else:
            out_port = datapath.ofproto.OFPP_FLOOD    #By flood, to find dst, when dst get packet, dst will send a new back,the graph will record dst info
            #print("8888888888 not find dst")
        return out_port

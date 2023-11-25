# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp, lldp
from ryu.lib.packet import ipv6
from ryu.lib import mac

from ryu.topology.api import get_switch, get_link
from ryu.topology import event, switches
import networkx as nx


class Broadcast_prevent(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Broadcast_prevent, self).__init__(*args, **kwargs)
        # self.mac_to_port = {}
        self.sw = {}
        self.topology_api_app = self
        self.network = nx.DiGraph()
        self.links = {}
        self.paths = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions, 0, 0, 0)
        self.logger.info("switch:%s connected", datapath.id)

    def add_flow(self, datapath, priority, match, actions, idle_time, hard_time, cookie):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                idle_timeout=idle_time, hard_timeout=hard_time,
                                match=match, instructions=inst, cookie=cookie)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        '''
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 2, match, actions, 0, 0, 0)
            return None
        '''

        if src not in self.network:
            self.network.add_node(src)
            self.network.add_edge(dpid, src, attr_dict={'port': in_port})
            self.network.add_edge(src, dpid)
            self.paths.setdefault(src, {})


        arp_pkt = pkt.get_protocol(arp.arp)

        if arp_pkt:
            if self.arp_handler(msg):
                return None
        lldp_pkt = pkt.get_protocol(lldp.lldp)
        if lldp_pkt:
            return

        # self.mac_to_port.setdefault(dpid, {})
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        eth_src = eth_pkt.src  # note: mac info willn`t  change in network
        eth_dst = eth_pkt.dst
        out_port = self.get_out_port(datapath, eth_src, eth_dst, in_port)
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.logger.info(" install flow_mod:%s -> %s ", in_port, out_port)

            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions, 0, 0, 1)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions,
                                  data=data)
        datapath.send_msg(out)
        print("..................find path...........................")
        self.logger.info("dpid:%s    src:%s      dst:%s      in_port:%s    out_port:%s", dpid, src, dst, in_port,
                         out_port)
        print("..................end path...........................")

    def get_out_port(self, datapath, src, dst, in_port):
        '''
        datapath: is current datapath info
        src,dst: both are the host info
        in_port: is current datapath in_port
        '''
        dpid = datapath.id

        # the first :Doesn`t find src host at graph
        if src not in self.network:
            self.network.add_node(src)
            self.network.add_edge(dpid, src, attr_dict={'port': in_port})
            self.network.add_edge(src, dpid)
            self.paths.setdefault(src, {})

        # second: search the shortest path, from src to dst host
        if dst in self.network:
            if dst not in self.paths[src]:  # if not cache src to dst path,then to find it
                path = nx.shortest_path(self.network, src, dst)
                self.paths[src][dst] = path

            path = self.paths[src][dst]
            next_hop = path[path.index(dpid) + 1]
            # print("1ooooooooooooooooooo")
            # print(self.network[dpid][next_hop])
            out_port = self.network[dpid][next_hop]['attr_dict']['port']
            # print("2ooooooooooooooooooo")
            # print(out_port)

            # get path info
            print("6666666666 find dst")
            print(path)
        else:
            out_port = datapath.ofproto.OFPP_FLOOD  # By flood, to find dst, when dst get packet, dst will send a new back,the graph will record dst info
            # print("8888888888 not find dst")
        return out_port

    def arp_handler(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        arp_pkt = pkt.get_protocol(arp.arp)

        if eth:
            eth_dst = eth.dst
            eth_src = eth.src
        if eth_dst == mac.BROADCAST_STR:
            # ARP broadcast storm prevent start
            arp_dst_ip = arp_pkt.dst_ip
            arp_src_ip = arp_pkt.src_ip
            # if arp packet already found before
            if (datapath.id, arp_src_ip, arp_dst_ip) in self.sw:
                # packet come from different port we stored.
                if self.sw[(datapath.id, arp_src_ip, arp_dst_ip)] != in_port:
                    datapath.send_packet_out(in_port=in_port, actions=[])
                    return True
            # ARP packet first time
            else:
                self.sw[(datapath.id, arp_src_ip, arp_dst_ip)] = in_port
                # self.mac_to_port.setdefault(datapath.id, {})
                # self.mac_to_port[datapath.id][eth_src] = in_port
        return False

    @set_ev_cls(event.EventSwitchEnter,[CONFIG_DISPATCHER,MAIN_DISPATCHER])
    def get_topology(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        switches = [switch.dp.id for switch in switch_list]
        self.network.add_nodes_from(switches)

        links_list = get_link(self.topology_api_app, None)

        links = [(link.src.dpid, link.dst.dpid, {'attr_dict': {'port': link.dst.port_no}}) for link in links_list]

        self.network.add_edges_from(links)
        links = [(link.src.dpid, link.dst.dpid, {'attr_dict': {'port': link.dst.port_no}}) for link in links_list]
        self.network.add_edges_from(links)
        print("links found: ")
        print(self.network.edges())


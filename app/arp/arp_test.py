from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import icmp
from ryu.lib.packet import ether_types
from ryu.lib import mac
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.topology.api import get_all_host, get_all_link, get_all_switch
from ryu.app.wsgi import ControllerBase
import networkx as nx


ETHERNET = ethernet.ethernet.__name__

ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"  # ARP 请求的地址

ARP = arp.arp.__name__


class GETSHORT_1(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # 初始化类变量：
    def __init__(self, *args, **kwargs):
        super(GETSHORT_1, self).__init__(*args, **kwargs)
        self.mac_table = {}  # 交换机的 MAC 表
        self.arp_table = {}  # arp 表

        self.topo_thread = hub.spawn(self._get_topology)  # 使用绿色线程来        执行_get_topology 函数
        self.graph = nx.DiGraph()  # 使用 networkx 创建一个图
        self.topology_api_app = self

        self.switch_host_port = {}  # 交换机和主机连接的端口
        self.datapath_switch = {}  # 交换机及其对应的 datapath

    def add_flow(self, datapath, priority, match, actions):
        dp = datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match, instructions=inst)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        pkt = packet.Packet(msg.data)
        dpid = dp.id
        in_port = msg.match['in_port']
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        if dpid not in self.datapath_switch:
            self.datapath_switch[dpid] = dp

        # 去除不需要的协议

        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return None

        if eth_pkt.ethertype == ether_types.ETH_TYPE_IPV6:
            return None

        # header_list = dict((p.protocol_name, p) for p in pkt.protocols if type(p) != str)
        header_list = dict(
            (p.protocol_name, p) for p in pkt.protocols if hasattr(p, 'protocol_name') and type(p) != str)
        # header_list = {p.name: p for p in pkt if p.name != 'Padding'}

        # 将未学习的 ARP 包向所有交换机与主机相连的端口转发
        if dst == ETHERNET_MULTICAST and ARP in header_list:
            self.arp_table[header_list[ARP].src_ip] = src
            arp_dst_ip = header_list[ARP].dst_ip
            # 未被学习过
            if arp_dst_ip not in self.arp_table:
                # 向其他所有交换机和主机相连接的端口转发
                for key in self.switch_host_port:
                    if key != dpid:
                        dp = self.datapath_switch[key]
                        for out_port in self.switch_host_port[key]:
                            out = parser.OFPPacketOut(
                                datapath=dp,
                                buffer_id=ofp.OFP_NO_BUFFER,
                                in_port=ofp.OFPP_CONTROLLER,
                                actions=[parser.OFPActionOutput(out_port)], data=msg.data)
                            dp.send_msg(out)
            # 已经学习过
            else:
                dst = self.arp_table[arp_dst_ip]

        self.mac_table.setdefault(dpid, {})
        if dst in self.mac_table[dpid]:
            out_port = self.mac_table[dpid][dst]
        else:
            out_port = ofp.OFPP_FLOOD

        # 将主机与交换机之间的连接加入到图中
        if src not in self.graph:
            self.graph.add_node(src)
            self.graph.add_edge(dpid, src, weight=0, port=in_port)
            self.graph.add_edge(src, dpid, weight=0)

        # 得到跳数最小的路径
        if src in self.graph and dst in self.graph and dpid in self.graph:

            # 直接使用 networkx 得到最短路径
            path = nx.shortest_path(self.graph, src, dst, weight="weight")

            # 如果当前的交换机不在最短路径上，丢弃该数据包
            if dpid not in path:
                return None

            nxt = path[path.index(dpid) + 1]
            out_port = self.graph[dpid][nxt]['port']
            self.mac_table[dpid][dst] = out_port
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(
                datapath=dp, buffer_id=ofp.OFP_NO_BUFFER, in_port=in_port, actions=actions, data=msg.data)
            dp.send_msg(out)

            # 到达目的地则输出路径
            if nxt == dst and dpid == path[-2]:
                print("path:", src, "->", dst)
                print("the length of the path is {}".format(len(path)))
                print(path[0], "->", end='')
                for item in path[1:-1]:
                    index = path.index(item)
                    print("{}:s{}:{}".format(self.graph[item][path[index - 1]]['port'], item,
                                             self.graph[item][path[index + 1]]['port']), end='')
                    print("->", end='')
                print(path[-1])
                print('\n')
                # print('switch_host_port')
                # print(self.switch_host_port)
                # print('datapath_switch')
                # print(self.datapath_switch)
                # print('header_list')
                # print(header_list)
                # print(path)
                print('\n')
                return None
            # else:
            # actions = [parser.OFPActionOutput(out_port)]
            # out = parser.OFPPacketOut(
            # datapath=dp, buffer_id=ofp.OFP_NO_BUFFER, in_port=in_port, actions=actions, data=msg.data)
            # dp.send_msg(out)

    def _get_topology(self):
        hub.sleep(2)  # 模仿网络请求等待

        # 获得整个网络的拓扑
        switch_list = get_switch(self.topology_api_app, None)
        switches = [switch.dp.id for switch in switch_list]
        self.graph.add_nodes_from(switches)
        link_list = get_link(self.topology_api_app, None)

        for link in link_list:
            self.graph.add_edge(link.src.dpid, link.dst.dpid, weight=1, port=link.src.port_no)
            self.graph.add_edge(link.dst.dpid, link.src.dpid, weight=1, port=link.dst.port_no)
            switch_all_port = {}

        for switch in switch_list:
            dpid = switch.dp.id  # 交换机 id
            flag = False
            for port in switch.ports:
                if flag:
                    switch_all_port[dpid].add(port.port_no)  # 获得端口            号
                    continue
                if (dpid not in switch_all_port):
                    switch_all_port[dpid] = {port.port_no}
                    flag = True
            # 去除交换机之间连接的端口
            for link in link_list:
                Src = link.src
                Dst = link.dst
                if Src.dpid in switch_all_port:
                    switch_all_port[Src.dpid].discard(Src.port_no)
                if Dst.dpid in switch_all_port:
                    switch_all_port[Dst.dpid].discard(Dst.port_no)
                self.switch_host_port = switch_all_port
        # 打印拓扑信息
        print("nodes:")
        print(self.graph.nodes())
        print("links:")
        print(self.graph.edges())
        print("topo:")
        print("node1      node2")

        for u, adj_u in self.graph.adj.items():
            for v, eattr in adj_u.items():
                if u < v:
                    self.logger.info('s%2s     s%2s', u, v)
        print("--------------------------------")


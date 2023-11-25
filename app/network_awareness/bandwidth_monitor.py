from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,DEAD_DISPATCHER
from ryu.lib import hub

class MyMonitor(simple_switch_13.SimpleSwitch13):    #simple_switch_13 is same as the last experiment which named self_learn_switch
    '''
    design a class to achvie managing the quantity of flow
    '''

    def __init__(self,*args,**kwargs):
        super(MyMonitor,self).__init__(*args,**kwargs)
        self.datapaths = {}
        #use gevent to start monitor
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER,DEAD_DISPATCHER])
    def _state_change_handler(self,ev):
        '''
        design a handler to get switch state transition condition
        '''
        #first get ofprocotol info
        datapath = ev.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        #judge datapath`s status to decide how to operate
        if datapath.state == MAIN_DISPATCHER:    #should save info to dictation
            if datapath.id not in self.datapaths:
                self.datapaths[datapath.id] = datapath
                self.logger.debug("Regist datapath: %16x",datapath.id)
        elif datapath.state == DEAD_DISPATCHER:    #should remove info from dictation
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]
                self.logger.debug("Unregist datapath: %16x",datapath.id)


    def _monitor(self):
        '''
        design a monitor on timing system to request switch infomations about port and flow
        '''
        while True:    #initiatie to request port and flow info all the time
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(5)    #pause to sleep to wait reply, and gave time to other gevent to request

    def _request_stats(self,datapath):
        '''
        the function is to send requery to datapath
        '''
        self.logger.debug("send stats reques to datapath: %16x for port and flow info",datapath.id)

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)


    @set_ev_cls(ofp_event.EventOFPPortStatsReply,MAIN_DISPATCHER)
    def _port_stats_reply_handler(self,ev):
        '''
        monitor to require the port state, then this function is to get infomation for port`s info
        print("6666666666port info:")
        print(ev.msg)
        print(dir(ev.msg))
        '''
        body = ev.msg.body
        self.logger.info('datapath             port     '
                        'rx_packets            tx_packets'
                        'rx_bytes            tx_bytes'
                        'rx_errors            tx_errors'
                        )
        self.logger.info('---------------    --------'
                        '--------    --------'
                        '--------    --------'
                        '--------    --------'
                        )
        for port_stat in sorted(body,key=attrgetter('port_no')):
                self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                    ev.msg.datapath.id,port_stat.port_no,port_stat.rx_packets,port_stat.tx_packets,
                    port_stat.rx_bytes,port_stat.tx_bytes,port_stat.rx_errors,port_stat.tx_errors
                        )


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply,MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self,ev):
        '''
        monitor to require the flow state, then this function is to get infomation for flow`s info
        print("777777777flow info:")
        print(ev.msg)
        print(dir(ev.msg))
        '''
        body = ev.msg.body

        self.logger.info('datapath             '
                        'in_port            eth_src'
                        'out_port            eth_dst'
                        'packet_count        byte_count'
                        )
        self.logger.info('---------------    '
                        '----    -----------------'
                        '----    -----------------'
                        '---------    ---------'
                        )
        for flow_stat in sorted([flow for flow in body if flow.priority==1],
                        key=lambda flow:(flow.match['in_port'],flow.match['eth_src'])):
                self.logger.info('%016x    %8x    %17s    %8x    %17s    %8d    %8d',
                    ev.msg.datapath.id,flow_stat.match['in_port'],flow_stat.match['eth_src'],
                    flow_stat.instructions[0].actions[0].port,flow_stat.match['eth_dst'],
                    flow_stat.packet_count,flow_stat.byte_count
                        )

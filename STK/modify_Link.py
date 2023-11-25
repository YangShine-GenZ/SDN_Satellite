from mininet.net import Mininet
from typing import Dict
import time

def get_next(n, m, n_max, m_max):
    n_ = (n+1)%n_max
    m_ = (m+1)%m_max
    return n_, m_


def modifyLink(net:Mininet, node1:str, node2:str, params1:Dict, params2:Dict=None):
    """

    利用params1和params2设置属性连接node1和node2的连接的属性，
    params1控制node1对应的intf
    params2控制node2对应的intf，若缺省则通params1


    参考 mininet.link.TCIntf.config()


    params1和params2的键值参考下面

    for all Intf:
        mac=None, 
        ip=None, 
        ifconfig=None,
        up=True

    only for TCIntf:
           bw: bandwidth in b/s (e.g. '10m')
           delay: transmit delay (e.g. '1ms' )
           jitter: jitter (e.g. '1ms')
           loss: loss (e.g. '1%' )
           gro: enable GRO (False)
           txo: enable transmit checksum offload (True)
           rxo: enable receive checksum offload (True)
           speedup: experimental switch-side bw option
           use_hfsc: use HFSC scheduling
           use_tbf: use TBF scheduling
           latency_ms: TBF latency parameter
           enable_ecn: enable ECN (False)
           enable_red: enable RED (False)
           max_queue_size: queue limit parameter for netem
    """
    h1 = net.getNodeByName( node1 )
    h2 = net.getNodeByName( node2 )

    links = h1.connectionsTo(h2)

    srcIntf = links[0][0]  # todo 判断有没有写错
    dstIntf = links[0][1]


    if not params2:
        #* 如果只修改node1，设置params2为非空字典，且不包含上面提到的参数
        params2 = params1
    srcIntf.config(**params1)
    dstIntf.config(**params2)


def modifyNode(net:Mininet, node1:str, node2:str, params1:Dict):
    """
    modify intf of node1 that is linked to node2
    parameters are in modifyLink()

    for all Intf:
        mac=None, 
        ip=None, 
        ifconfig=None,
        up=True
    """
    modifyLink(net, node1, node2, params1, params2=None)

def set_ip_table(net, node1, node2):
    h1 = net.getNodeByName( node1 )
    h2 = net.getNodeByName( node2 )

    links = h1.connectionsTo(h2)

    Intf1 = links[0][0]
    Intf2 = links[0][1]

    ip1 = Intf1.IP()
    ip2 = Intf2.IP()

    name1 = Intf1.name
    name2 = Intf2.name

    h1.cmd(f'ip r del 10.0.0.0/8 dev {name1}')
    # time.sleep(0.5)
    command = f'ip r add {ip2}/32 dev {name1} src {ip1}'
    h1.cmd(command)
    # time.sleep(0.5)
    print(f'{node1}--->{command}')

    h2.cmd(f'ip r del 10.0.0.0/8 dev {name2}')
    # time.sleep(0.5)
    command = f'ip r add {ip1}/32 dev {name2} src {ip2}'
    h2.cmd(command)
    print(f'{node2}--->{command}')



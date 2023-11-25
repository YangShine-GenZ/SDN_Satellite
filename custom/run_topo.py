from flask import Flask, request

from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI
from threading import Thread

from STK import config

from STK.modify_Link import modifyNode, get_next, set_ip_table


from topology import STKTopo
# from test import STKTopo


app = Flask(__name__)

topo={'topo':None}


# # 使用方法 requests.get(r'http://ip:8000/create/轨道数/轨道卫星数')
# @app.route('/create/<int:n>/<int:m>')
# def creat(n,m):
#     setLogLevel( 'info' )
#     info( '*** Creating network\n' )
#     net = Mininet(topo=STKTopo(n,m))
#     topo['topo'] = net
    
#     net.start()
    
#     t = Thread(target=CLI, args=(net, ), daemon=True)
#     t.start()

#     # CLI( net )

#     return 'created'


# # 使用方法 requests.get(r'http://ip:8000/stop/')
# @app.route('/stop/')
# def stop():
#     topo['topo'].stop()
#     return 'stopped'



# 使用方法 requests.post(r'http://ip:8000/modify/', data = param_list)
# param_list 由若干个字典构成,每个字典包含{node1, node2, bw, delay, jitter, loss}
# node1 node2 是要调整链接的两颗卫星
@app.route('/modify/', methods=['POST'])
def modify():
    modify_list = request.get_json()

    print(type(modify_list))
    print(modify_list)

    if not isinstance(modify_list, list):
        modify_list = list(modify_list)

    for param in modify_list:
        node1 = param.get('node1')
        node2 = param.get('node2')
        modifyNode(topo['topo'], node1, node2, param)

    return 'modify finish'


if __name__ == "__main__":


    setLogLevel( 'info' )
    info( '*** Creating network\n' )
    net = Mininet(topo=STKTopo(config.n, config.m))
    topo['topo'] = net
    
    net.start()
    
    t = Thread(target=app.run, args=('0.0.0.0', '8000'), daemon=True)
    t.start()

    for n in range(config.n):
            for m in range(config.m): 
                n_, m_ = get_next(n, m, config.n, config.m)
                node1 = f'node_{n}-{m}'
                node2 = f'node_{n}-{m_}'
                # node3 = f'node_{n_}-{m}'

                set_ip_table(net, node1, node2)
                # set_ip_table(net, node1, node3)

    CLI( net )

    net.stop()
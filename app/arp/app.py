from flask import Flask, request
from topology import STKTopo
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI
from threading import Thread

from STK.modify_Link import modifyNode


app = Flask(__name__)

topo={'topo':None}


# 使用方法 requests.get(r'http://ip:8000/create/轨道数/轨道卫星数')
@app.route('/create/<int:n>/<int:m>')
def creat(n,m):
    setLogLevel( 'info' )
    info( '*** Creating network\n' )
    net = Mininet(topo=STKTopo(n,m))
    topo['topo'] = net
    
    net.start()
    
    t = Thread(target=CLI, args=(net, ), daemon=True)
    t.start()

    # CLI( net )

    return 'created'


# 使用方法 requests.get(r'http://ip:8000/stop/')
@app.route('/stop/')
def stop():
    topo['topo'].stop()
    return 'stopped'



# 使用方法 requests.post(r'http://ip:8000/modify/', data = param_list)
# param_list 由若干个字典构成,每个字典包含{node1, node2, bw, delay, jitter, loss}
# node1 node2 是要调整链接的两颗卫星
@app.route('/modify/', methods=['POST'])
def modify():
    modify_list = request.form.get('modify_list')
    if not isinstance(modify_list, list):
        modify_list = list(modify_list)

    for param in modify_list:
        node1 = param.get('node1')
        node2 = param.get('node1')
        modifyNode(topo['topo'], node1, node2, param)

    return 'modify finish'


if __name__ == "__main__":
    app.run('0.0.0.0', '8000')
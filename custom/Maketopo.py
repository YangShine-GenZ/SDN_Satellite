from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI

from STK import config

from newtopo import STKTopo

# from test import STKTopo


#app = Flask(__name__)

topo = {'topo': None}


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





if __name__ == "__main__":

    setLogLevel('info')
    info('*** Creating network\n')
    net = Mininet(topo=STKTopo(config.n, config.m))
    topo['topo'] = net

    net.start()




    CLI(net)

    net.stop()
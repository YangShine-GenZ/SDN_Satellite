

from mininet.topo import Topo
from mininet.link import TCIntf

from STK.modify_Link import get_next

from STK import config


#!  卫星node的ip分配问题, 分配node的时候会默认分配ip

class STKTopo(Topo):
    def build(self, n_obit, sat_per_obit):
        self.node_list = [[] for i in range(n_obit) ]
        self.host_list = []



        # 创建node
        for n in range(n_obit):
            for m in range(sat_per_obit):
                ip_ = f'10.{n}.{m}.1' # 用于连接中继卫星
                node = self.addSwitch(f'node_{n}-{m}', ip = ip_)
                self.node_list[n].append(node)


        # link
        for n in range(n_obit):
            for m in range(sat_per_obit):
                this_node = self.node_list[n][m]
                n_, m_ = get_next(n,m, n_obit, sat_per_obit)
                next_node1 = self.node_list[n][m_]
                next_node2 = self.node_list[n_][m]
                self.addLink(this_node,
                            next_node1,
                            intf=TCIntf,
                            params1={ #? ip最后一位, 1,2,3,4 分别对应 右 下 左 上
                                'ip': f'10.{n}.{m}.2/8',  # 连接右侧卫星
                                'bw': config.bw,
                                'delay': config.delay,
                                'jitter': config.jitter,
                                'loss': config.loss
                            },
                            params2={
                                'ip': f'10.{n}.{m_}.3/8',  # 连接左侧卫星
                                'bw': config.bw,
                                'delay': config.delay,
                                'jitter': config.jitter,
                                'loss': config.loss
                            }
                            )

                #* 只考虑同轨道面的通信，跨轨道面的改用中继卫星
                self.addLink(this_node,
                             next_node2,
                             intf=TCIntf,
                             params1={
                                 'ip': f'10.{n}.{m}.2/8',
                                 'bw': config.bw,
                                 'delay': config.delay,
                                 'jitter': config.jitter,
                                 'loss': config.loss
                             },
                             params2={
                                 'ip': f'10.{n_}.{m}.4/8',
                                 'bw': config.bw,
                                 'delay': config.delay,
                                 'jitter': config.jitter,
                                 'loss': config.loss
                             })
                h1 = self.addHost(f'host_{n}_{m}_1')
                h2 = self.addHost(f'host_{n}_{m}_2')
                self.addLink(this_node,h1)
                self.addLink(this_node,h2)
                self.host_list.append(h1)
                self.host_list.append(h2)
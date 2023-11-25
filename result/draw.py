import re
import matplotlib.pyplot as plt
import numpy as np
from statistics import mean

import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["SimHei"] #设置字体
plt.rcParams["axes.unicode_minus"]=False #该语句解决图像中的“-”负号的乱码问题

time_my_list = []
rate_my_list = []
time_delay_list = []
rate_delay_list = []
time_hop_list = []
rate_hop_list = []


with open('result_my.txt', 'r') as f:# iperf-log.txt为iperf日志文件名
    row_data = f.readlines() # 读取iperf日志文件的每一行至一个list中
    print(row_data)
    for line in row_data:    # 利用正则表达式进行匹配，可根据实际情况更改匹配内容
        time = re.findall(r"-(.*) sec", line)
        rate = re.findall(r"MBytes  (.*) Mbits", line)
        if(len(rate)<=0):
              rate = re.findall(r"KBytes  (.*) Kbits", line)
        print("time:",time," rate:",rate)
        if(len(time)>0):     # 当前行中有吞吐和时间数据时对数据进行存储
            print(time)
            time_my_list.append(float(time[0]))
            rate_my_list.append(float(rate[0]))

with open('result_hop.txt', 'r') as f:# iperf-log.txt为iperf日志文件名
    row_data = f.readlines() # 读取iperf日志文件的每一行至一个list中
    print(row_data)
    for line in row_data:    # 利用正则表达式进行匹配，可根据实际情况更改匹配内容
        time = re.findall(r"-(.*) sec", line)
        rate = re.findall(r"MBytes  (.*) Mbits", line)
        if(len(rate)<=0):
              rate = re.findall(r"KBytes  (.*) Kbits", line)
        print("time:",time," rate:",rate)
        if(len(time)>0):     # 当前行中有吞吐和时间数据时对数据进行存储
            print(time)
            time_hop_list.append(float(time[0]))
            rate_hop_list.append(float(rate[0]))


with open('result_delay.txt', 'r') as f:# iperf-log.txt为iperf日志文件名
    row_data = f.readlines() # 读取iperf日志文件的每一行至一个list中
    print(row_data)
    for line in row_data:    # 利用正则表达式进行匹配，可根据实际情况更改匹配内容
        time = re.findall(r"-(.*) sec", line)
        rate = re.findall(r"MBytes  (.*) Mbits", line)
        if(len(rate)<=0):
              rate = re.findall(r"KBytes  (.*) Kbits", line)
        print("time:",time," rate:",rate)
        if(len(time)>0):     # 当前行中有吞吐和时间数据时对数据进行存储
            print(time)
            time_delay_list.append(float(time[0]))
            rate_delay_list.append(float(rate[0]))

print("Average_my:",mean(rate_my_list))
print("Average_ECMP:",mean(rate_hop_list))
print("Average_hop:",mean(rate_delay_list))


plt.figure()

#plt.plot(time_my_list, rate_my_list,label='Joint resource optimization algorithm')
#plt.plot(time_hop_list, rate_hop_list,label='ECMP')
#plt.plot(time_delay_list, rate_delay_list,label='Dijkstra')
plt.plot(time_my_list, rate_my_list,label='网络资源联合优化算法')
plt.plot(time_hop_list, rate_hop_list,label='负载均衡ECMP算法')
plt.plot(time_delay_list, rate_delay_list,label='改进迪杰斯特拉算法')
#plt.xlabel('Time(sec)')
plt.xlabel('时间（sec）')
#plt.ylabel('ThroughPut(Mbits/sec)')
plt.ylabel('吞吐量(Mbits/sec)')
plt.legend(loc='best')
plt.show()

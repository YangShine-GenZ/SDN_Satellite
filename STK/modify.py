import requests
import json

param = {'node1':'node_0-0','node2':'mid1','bw': 1,'delay':'1ms', 'jitter':'50ms', 'loss':1}


data_list = []
data_list.append(param)
data_list = json.dumps(data_list)
print(data_list)
headers = {
    "Content-Type": "application/json;charset=utf8"
}
#http://127.0.0.1:8000/modify/
response = requests.post('http://192.168.56.135:8000/modify/', data = data_list,headers=headers)

print(response.text)

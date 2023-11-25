sudo apt-get install -y git ssh python3-pip curl net-tools vim 

sudo rm /usr/bin/python
sudo ln -s /usr/bin/python3 /usr/bin/python

sudo ln -s /usr/bin/pip3 /usr/bin/pip

# # config pip
# mininet run as root, so only sudo pip works.
sudo pip install pip -U
sudo pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
sudo pip install flask requests




echo -e "########################################################"
echo -e "                  install mininet"
echo -e "########################################################"
sleep 2


cd ~
git clone git://github.com/mininet/mininet.git
cd mininet

git checkout -b mininet-2.3.0 2.3.0
bash ~/mininet/util/install.sh -a
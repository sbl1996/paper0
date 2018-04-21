import requests
import pandas as pd
import networkx as nx

from requests import Session
from pandas.io.json import json_normalize

from crawler import ZhihuCrawler

cookies = {
  'z_c0': '"2|1:0|10:1523854628|4:z_c0|92:Mi4xNV8wSUFRQUFBQUFBd0dDM2V5UnpEU1lBQUFCZ0FsVk5KSHZCV3dCWUg2c2FVSE9kWW01a2RYVzRoa2xBWUNsWDlR|1bc25bbaa821e106c1ff059a8781dca41e53ea70ad1cebb02aa332b789a92ebf"',
  '_xsrf': '97250175-8ea7-415e-8e7f-b924ee86247'
}
user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
jar = requests.cookies.RequestsCookieJar()
for k, v in cookies.items():
  jar.set(k, v)
sess = Session()
sess.cookies = jar
sess.headers['User-Agent'] = user_agent
g = nx.DiGraph()

craw = ZhihuCrawler(sess=sess)
craw.member_info('li-mu-23')

data = craw.subscribed_topics('chen-bi-luo-74')
df = json_normalize(data)

def draw(g, **kwargs):
  fig, ax = plt.subplots(1, 1, figsize=(8, 8))
  pos = nx.spring_layout(g, k=0.01, **kwargs)
  labels = dict(g.nodes('name'))
  nx.draw(g, labels=labels, node_size=100 * topics.weight, pos=pos, ax=ax,
          font_size=12, node_color='skyblue')

def savefig(path, g, figsize, **kwargs):
  plt.ioff()
  fig, ax = plt.subplots(1, 1, figsize=figsize)
  labels = dict(g.nodes('name'))
  pos = nx.spring_layout(g, **kwargs)
  nx.draw(g, pos=pos, labels=labels, ax=ax)
  fig.savefig(path)
  plt.ion()
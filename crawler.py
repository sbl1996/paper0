import requests
import logging
from pymongo import MongoClient
import inspect

def mongod(func):
    f_code = func.__code__
    f_name = func.__name__
    varnames = f_code.co_varnames
    def wrapper(*args):
      coll = args[0].db[f_name]
      filters = dict(zip(varnames[1:], args[1:]))
      data = coll.find_one(filters)
      if data:
        return data
      else:
        data = func(*args)
        coll.insert_one(data)
        return data
    return wrapper

class ZhihuCrawler():
  def __init__(self, sess, client=None):
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT)
    
    self.log = logging.getLogger('ZhihuCrawler')
    self.log.setLevel('INFO')
    self.sess = sess
    self.xsrf = sess.cookies['_xsrf']

    self.mongo = client or MongoClient()
    self.db = self.mongo.zhihu_database

  def _get(self, url):
    self.log.info('GET %s', url)
    return self.sess.get(url)

  def _post(self, url, data=None):
    self.log.info('POST %s', url)
    return self.sess.post(url, data=data)

  def _url_rewrite(self, url):
    if 'api' in url:
      return url
    parts = url.split('/')
    parts.insert(3, 'v4')
    parts.insert(3, 'api')
    return '/'.join(parts)

  def _api_v4(self, start_url):
    url = self._url_rewrite(start_url)
    res = []

    is_end = False
    while not is_end:
      response = self._get(url)
      obj = response.json()
      paging = obj['paging']
      data = obj['data']
      res += data

      url = self._url_rewrite(paging['next'])
      is_end = paging['is_end']
    return res

  def _members_api(self, path, url_token):
    url = 'https://www.zhihu.com/api/v4/members/%s%s?limit=20&offset=0' % (url_token, path)
    return self._api_v4(url)

  @mongod
  def subscribed_topics(self, url_token):
    data = self._members_api('/following-topic-contributions', url_token)
    for i, d in enumerate(data):
      d['topic']['contributions'] = d['contributions_count']
      data[i] = d['topic']
    return {
      'url_token': url_token,
      'list': data
    }

  @mongod
  def followees(self, url_token):
    data = self._members_api('/followees', url_token)
    return {
      'url_token': url_token,
      'list': data
    }

  @mongod
  def followers(self, url_token):
    data = self._members_api('/followers', url_token)
    return {
      'url_token': url_token,
      'list': data
    }

  def following_questions(self, url_token):
    url = f'https://www.zhihu.com/api/v4/members/{url_token}/following-questions?include=data%5B%2A%5D.topics&limit=20&offset=0'
    data = self._api_v4(url)
    return {
      'url_token': url_token,
      'list': data
    }    

  @mongod
  def member_info(self, url_token):
    url = f'https://www.zhihu.com/api/v4/members/{url_token}?include=answer_count%2Cincluded_answers_count%2Cfavorited_count%2Cfollower_count%2Cthanked_count%2Cvoteup_count%2Cincluded_articles_count%2Carticles_count%2Cbadge%5B%3F(type%3Dbest_answerer)%5D.topics'
    return self._get(url).json()

  @mongod
  def topic_children(self, id):
    url = 'https://www.zhihu.com/api/v4/topics/%s/children' % id
    children = self._api_v4(url)
    children = list(map(lambda c: { 'id': c['id'], 'name': c['name'] }, children))
    return {
      'id': id,
      'list': children
    }

  @mongod
  def topic_parents(self, id):
    url = 'https://www.zhihu.com/api/v4/topics/%s/parent' % id
    parents = self._api_v4(url)
    parents = list(map(lambda p: { 'id': p['id'], 'name': p['name'] }, parents))
    return {
      'id': id,
      'list': parents
    }

  def topic_around(self, id, dg, depth=1):
    topic = self.topic_info(id)
    name = topic['name']
    topic = {
      'id': id,
      'name': name
    }
    if not dg.has_node(topic['id']):
        dg.add_node(topic['id'], name=topic['name'])
    topic['children'] = self.topic_children(id)
    for child in topic['children']:
      if not dg.has_node(child['id']):
        dg.add_node(child['id'], name=child['name'])
      dg.add_edge(child['id'], topic['id'])
    topic['parents'] = self.topic_parents(id)
    for p in topic['parents']:
      if not dg.has_node(p['id']):
        dg.add_node(p['id'], name=p['name'])
      dg.add_edge(topic['id'], p['id'])
    return topic


  @mongod
  def topic_info(self, id):
    url = f'https://www.zhihu.com/api/v4/topics/{id}?include=questions_count%2Cbest_answers_count%2Cfollowers_count'
    obj = self._get(url).json()
    return obj

  def topic_hierarchy(self, id, dg, name=None):
    if not name:
      topic = self.topic_info(id)
      name = topic['name']
    root = {
      'id': id,
      'name': name
    }
    root['children'] = self.topic_children(id)['list']
    if not dg.has_node(root['id']):
      dg.add_node(root['id'], name=root['name'])
    root['children'] = list(map(lambda t: self.topic_hierarchy(t['id'], dg, t['name']), root['children']))
    for child in root['children']:
      if not dg.has_node(child['id']):
        dg.add_node(child['id'], name=child['name'])
      dg.add_edge(child['id'], root['id'])
    return root
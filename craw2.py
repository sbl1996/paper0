import requests

class Craw2(object):
  def __init__(self, sess, g):
    super(Craw2, self).__init__()
    self.sess = sess
    self.xsrf = sess.cookies['_xsrf']
    self.g = g

  def _process_topic(self, obj):
    data = obj['msg']
    topic = {}

    topic_name, topic_id = data[0][1:]
    topic['name'] = data[0][1]
    topic['id'] = data[0][2]
    children = data[1]
    if len(children) == 0:
      topic['children'] = children
      return topic, None, None
    paging = children[-1][0]
    if len(paging) == 4:
      topic['children'] = list(map(lambda s: { 'name': s[0][1], 'id': s[0][2] }, children[:-1]))
      next_children, next_parent = paging[2:]
      return topic, next_children, next_parent
    else:
      topic['children'] = list(map(lambda s: { 'name': s[0][1], 'id': s[0][2] }, children))
      return topic, None, None


  def get_topic_organize(self, child, parent):
    def callback(sess, rep):
      obj = rep.json()
      result, next_child, next_parent = self._process_topic(obj)
      if not self.g.has_node(result['id']):
        self.g.add_node(result['id'], name=result['name'])
      for child in result['children']:
        if not self.g.has_node(child['id']):
          self.g.add_node(child['id'], name=child['name'])
          self.get_topic_organize('', child['id'])
        self.g.add_edge(child['id'], result['id'])
      if next_child is not None:
        if self.g.degree(next_parent) >= 100:
          self.log.warn('Topic %s has more than 100 children', next_parent)
        else:
          self.get_topic_organize(next_child, next_parent)
    url = f'https://www.zhihu.com/topic/19776749/organize/entire?child={child}&parent={parent}'
    self.sess.post(url, data={'_xsrf': self.xsrf}, background_callback=callback)
    
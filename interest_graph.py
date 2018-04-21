import networkx as nx
from networkx.readwrite import json_graph
from toolz import curry

def interp_contribs(x):
  """
  xs = [0 1  5 10 20]
  ys = [1 5 15 25 40]
  p = scipy.polyfit(xs, ys, 5)
  """
  y = 0
  p = np.array([-9.11362377e-05,  6.03351864e-03, -1.59796058e-01,  3.44830124e+00,
        1.00000000e+00])
  y += np.polyval(p, x) * (x <= 20)
  y += (x + 20) * (x > 20)
  return y

def interp_follows(x):
  return x

def interp_questions(x):
  return x

def normalize(xs, scale=1.0):
  return xs * scale / xs.sum()

def interest_graph(name, alpha=0.5, beta=0.5):
  """
  Returns the interest graph of user

  Parameters
  ----------
  name : str
      Name of user.
  alpha : float
      Factor of CONTRIBS.

  Returns
  -------
  g : nx.DiGraph
    Interest graph of user
  """
  # Data Preparation
  topics = craw.subscribed_topics(name)['list']
  topics = pd.DataFrame(topics)

  if len(topics) == 0:
    return nx.DiGraph(), topics
  contribs = topics.contributions
  contribs_score = interp_contribs(contribs)
  contribs_score = normalize(contribs_score)
  topics['contrib'] = contribs_score

  infos = topics.id.apply(craw.topic_info)
  infos = pd.DataFrame(list(infos))
  follows = infos.followers_count
  questions = infos.questions_count
  follows_score = normalize(interp_follows(follows))
  questions_score = normalize(interp_questions(questions))
  topics['follows_score'] = follows_score
  topics['questions_score'] = questions_score

  infl = beta * follows_score + (1 - beta) * questions_score
  topics['infl'] = infl

  weight = (alpha * infl + (1-alpha) * contribs_score) * 100
  topics['weight'] = weight

  g = nx.DiGraph()
  for t in topics.itertuples():
    g.add_node(t.id, name=t.name, weight=t.weight)

  for id in g.nodes:
    parents = craw.topic_parents(id)['list']
    for p in parents:
      print(p['id'])
      if g.has_node(p['id']):
        g.add_edge(id, p['id'])


  return g, topics

def save_interest_graph(coll, name, g, topics):
  g_data = json_graph.node_link_data(g, {'link': 'edges', 'source': 'from', 'target': 'to'})
  topics = topics[['contributions', 'id', 'name', 'contribs_score', 'follows_score', 'weight']]
  topics = topics.to_dict('records')
  data = {
    'name': name,
    'graph': g_data,
    'topics': topics
  }
  coll.insert_one(data)

@curry
def fscore(member, k_t=10, k_f=5, C=5, r_included=0.1):
  voteup = member.voteup_count
  thanked = member.thanked_count
  favorited = member.favorited_count
  answers = member.answer_count
  included = member.included_answers_count

  F = (voteup + k_t * thanked + k_f * favorited) / (answers + C) * (1 + included * r_included)
  return F

def clip(xs, k=0.3):
  r = k / (1 - k)
  while xs.max() / xs.sum() > 1.1 * k:
    xs = np.clip(xs, 0, r * (xs.sum() - xs))
  return xs

def followee_weights(followee_infos, alpha=0.5):
  df = pd.DataFrame(followee_infos)
  fscores = df.apply(fscore, axis=1)
  fscores = clip(fscores)
  fscores = normalize(fscores)
  follows = df.follower_count
  follows = clip(follows)
  follows = normalize(follows)

  w = alpha * fscores + (1 - alpha) * follows
  return w

def union(g0, g, w):
  for id in g.nodes:
    if g0.has_node(id):
      g0.nodes[id]['weight'] += w * g.nodes[id]['weight']
    else:
      g0.add_node(id, **g.nodes[id])

def get_weight(g):
  return pipe(g.nodes('weight'), list, pluck(1), list, np.array)

def union_all(gs, weights):
  g = nx.DiGraph()
  for i in range(len(gs)):
    union(g, gs[i], ws[i])
  for id in g.nodes:
    parents = craw.topic_parents(id)['list']
    for p in parents:
      if g.has_node(p['id']):
        g.add_edge(id, p['id'])
  return g

def subgraph(g0, wmin):
  g = nx.DiGraph()
  for id in g0.nodes:
    if g0.nodes[id]['weight'] > wmin:
      g.add_node(id, **g0.nodes[id])
  for id in g.nodes:
    parents = craw.topic_parents(id)['list']
    for p in parents:
      if g.has_node(p['id']):
        g.add_edge(id, p['id'])
  return g


@curry
def load_interest_graph(coll, name):
  data = coll.find_one({'name': name})
  if data:
    g_data = data['graph']
    g = json_graph.node_link_graph(g_data, attrs={'link': 'edges', 'source': 'from', 'target': 'to'})
    topics = data['topics']
    topics = pd.DataFrame(topics)
    return g, topics
  return None



def potential_interest_graph(name):
  followees = craw.followees(name)['list']
  followees = pd.DataFrame(followees)
  fnames = followees.url_token
  infos = lmap(craw.member_info, fnames)
  infos = pd.DataFrame(infos)
  ws = followee_weights(infos)

  gs, topicss = zip(*map(interest_graph, fnames))
from toolz import curry, map
from toolz.curried import get

@curry
def subdict(keys, d):
  nd = {}
  for k in keys:
    nd[k] = d[k]
  return nd

def lmap(f, xs):
  return list(map(f, xs))

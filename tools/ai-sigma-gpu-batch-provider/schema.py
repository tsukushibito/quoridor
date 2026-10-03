"""NN0 validation shared only by mock checks; production provider validates locally."""
def validate(items):
 assert isinstance(items,list) and 1<=len(items)<=8
 ids=[x['id'] for x in items];assert len(set(ids))==len(ids)
 for x in items:
  b=x['features_bits648'];assert len(b)==648 and all(type(v)==int and 0<=v<2**32 and (v&0x7f800000)!=0x7f800000 for v in b)

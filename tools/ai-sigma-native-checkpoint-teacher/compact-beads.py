import json,sys
x=json.load(sys.stdin)[0]
print(json.dumps([{k:x.get(k) for k in ['id','status','labels','assignee','updated_at']}]))

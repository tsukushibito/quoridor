import sys,time,json
print(json.dumps({"ready":True,"implementation":time.get_clock_info("monotonic").implementation,"resolution":time.get_clock_info("monotonic").resolution}),flush=True)
for line in sys.stdin:
 print(json.dumps({"monotonic_ms":time.monotonic_ns()/1e6}),flush=True)

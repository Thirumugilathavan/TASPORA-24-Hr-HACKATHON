import os
import time
import urllib.request
import json

TOKEN = os.environ.get("VERCEL_TOKEN", "")

for i in range(15):
    time.sleep(5)
    req = urllib.request.Request("https://api.vercel.com/v6/deployments?limit=2", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
    deps = res.get("deployments", [])
    states = [f"{d.get('name')}: {d.get('state')} ({d.get('url')})" for d in deps]
    print(f"Check {i+1}:", " | ".join(states))
    if all(d.get("state") in ["READY", "ERROR"] for d in deps):
        print("\nAll builds reached final state!")
        break

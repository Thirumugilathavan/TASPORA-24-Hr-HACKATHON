import os
import urllib.request
import json

TOKEN = os.environ.get("VERCEL_TOKEN", "")
TEAM_ID = "team_hZFY41JOno3O30hj16T1dhmz"

url = f"https://api.vercel.com/v6/deployments?teamId={TEAM_ID}&limit=5"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())

for d in data.get("deployments", []):
    name = d.get("name", "")
    state = d.get("state", "")
    durl = d.get("url", "")
    created = d.get("createdAt", 0)
    print(f"{name:30s} {state:12s} {durl}")

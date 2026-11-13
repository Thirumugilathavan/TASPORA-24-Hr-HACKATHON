import os
import urllib.request
import urllib.error
import json

TOKEN = os.environ.get("VERCEL_TOKEN", "")

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.read().decode())
        return None

res = get("https://api.vercel.com/v6/deployments?limit=15")
print("Total deployments:", len(res.get("deployments", [])))
for d in res.get("deployments", []):
    sha = d.get("meta", {}).get("githubCommitSha", "")[:7]
    ref = d.get("meta", {}).get("githubCommitRef", "")
    print(f"{d.get('name'):<15} | {d.get('uid')} | {d.get('state'):<10} | {sha:<7} | {ref:<35} | {d.get('url')}")

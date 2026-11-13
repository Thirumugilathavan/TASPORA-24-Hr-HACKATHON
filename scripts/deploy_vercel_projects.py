import os
import urllib.request
import urllib.error
import json
import time

TOKEN = os.environ.get("VERCEL_TOKEN", "")
TEAM_ID = "team_hZFY41JOno3O30hj16T1dhmz"

def api_call(url, data=None, method="GET"):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    encoded_data = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} on {method} {url}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Exception on {method} {url}: {e}")
        return None

print("1. Creating nalam-backend project...")
backend_payload = {
    "name": "nalam-backend",
    "framework": None,
    "gitRepository": {
        "type": "github",
        "repo": "Thirumugilathavan/TASPORA-24-Hr-HACKATHON"
    },
    "environmentVariables": [
        {"key": "ENVIRONMENT", "value": "production", "type": "plain", "target": ["production", "preview", "development"]},
        {"key": "DATABASE_URL", "value": "sqlite+aiosqlite:////tmp/carebridge.db", "type": "plain", "target": ["production", "preview", "development"]},
        {"key": "CORS_ORIGINS", "value": "[\"*\"]", "type": "plain", "target": ["production", "preview", "development"]}
    ]
}

res_b = api_call(f"https://api.vercel.com/v9/projects?teamId={TEAM_ID}", data=backend_payload, method="POST")
if res_b:
    print(f"Backend project created successfully: ID={res_b.get('id')}, Name={res_b.get('name')}")
else:
    print("Backend project creation failed.")

print("\n2. Creating nalam-frontend project...")
frontend_payload = {
    "name": "nalam-frontend",
    "framework": "vite",
    "rootDirectory": "frontend",
    "gitRepository": {
        "type": "github",
        "repo": "Thirumugilathavan/TASPORA-24-Hr-HACKATHON"
    }
}

res_f = api_call(f"https://api.vercel.com/v9/projects?teamId={TEAM_ID}", data=frontend_payload, method="POST")
if res_f:
    print(f"Frontend project created successfully: ID={res_f.get('id')}, Name={res_f.get('name')}")
else:
    print("Frontend project creation failed.")

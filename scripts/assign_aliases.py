import os
import urllib.request
import urllib.error
import json

TOKEN = os.environ.get("VERCEL_TOKEN", "")
TEAM_ID = "team_hZFY41JOno3O30hj16T1dhmz"

# Get latest deployments for backend and frontend
req = urllib.request.Request("https://api.vercel.com/v6/deployments?limit=2", headers={"Authorization": f"Bearer {TOKEN}"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())

backend_dep = next(d for d in res["deployments"] if d["name"] == "nalam-backend")
frontend_dep = next(d for d in res["deployments"] if d["name"] == "nalam-frontend")

print("Backend deployment:", backend_dep["uid"], backend_dep["url"])
print("Frontend deployment:", frontend_dep["uid"], frontend_dep["url"])

def assign_alias(dep_id, alias):
    url = f"https://api.vercel.com/v2/deployments/{dep_id}/aliases?teamId={TEAM_ID}"
    data = json.dumps({"alias": alias}).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Assigned alias '{alias}' to {dep_id}:", resp.status)
            return True
    except urllib.error.HTTPError as e:
        print(f"Error assigning alias '{alias}' to {dep_id}: {e.code} - {e.read().decode()}")
        return False

# Assign domains / aliases to project
def add_project_domain(project_id, domain):
    url = f"https://api.vercel.com/v9/projects/{project_id}/domains?teamId={TEAM_ID}"
    data = json.dumps({"name": domain}).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Added project domain '{domain}' to project {project_id}:", resp.status)
            return True
    except urllib.error.HTTPError as e:
        print(f"Error adding domain '{domain}' to project {project_id}: {e.code} - {e.read().decode()}")
        return False

# First add project domains to the projects:
add_project_domain(backend_dep["projectId"], "nalam-backend.vercel.app")
add_project_domain(frontend_dep["projectId"], "nalam-frontend-ten.vercel.app")
add_project_domain(frontend_dep["projectId"], "nalam-frontend.vercel.app")

# Then assign aliases to the specific deployments
assign_alias(backend_dep["uid"], "nalam-backend.vercel.app")
assign_alias(frontend_dep["uid"], "nalam-frontend-ten.vercel.app")
assign_alias(frontend_dep["uid"], "nalam-frontend.vercel.app")

import urllib.request
import urllib.error
import json

BASE_FRONTEND = "https://nalam-frontend-ten.vercel.app"
BASE_BACKEND = "https://nalam-backend.vercel.app"

def test_endpoint(name, url, method="GET", body=None, expected_status=200):
    headers = {"User-Agent": "NALAM-Verifier/1.0"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            status = r.status
            content = r.read().decode("utf-8", errors="replace")
            print(f"[{'PASS' if status == expected_status else 'FAIL'}] {name}")
            print(f"       URL: {url}")
            print(f"       Status: {status} (expected {expected_status})")
            print(f"       Preview: {content[:120].strip()}\n")
            return status == expected_status
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="replace")
        print(f"[{'PASS' if e.code == expected_status else 'FAIL'}] {name}")
        print(f"       URL: {url}")
        print(f"       Status: {e.code} (expected {expected_status})")
        print(f"       Preview: {content[:120].strip()}\n")
        return e.code == expected_status
    except Exception as ex:
        print(f"[FAIL] {name} - Exception: {ex}\n")
        return False

print("="*65)
print("NALAM PRODUCTION FRONTEND-TO-BACKEND INTEGRATION TESTS")
print("="*65)

results = [
    test_endpoint("1. Frontend SPA Root HTML", f"{BASE_FRONTEND}/", expected_status=200),
    test_endpoint("2. Frontend SPA Deep Route (/facilities)", f"{BASE_FRONTEND}/facilities", expected_status=200),
    test_endpoint("3. Frontend Proxy -> Backend API Root (/api)", f"{BASE_FRONTEND}/api", expected_status=200),
    test_endpoint("4. Frontend Proxy -> Backend Health (/api/health)", f"{BASE_FRONTEND}/api/health", expected_status=200),
    test_endpoint("5. Frontend Proxy -> Backend Villages Search", f"{BASE_FRONTEND}/api/villages/search?q=Tiruchengode", expected_status=200),
    test_endpoint("6. Frontend Proxy -> Backend Auth Login (Validation rejection test)", f"{BASE_FRONTEND}/api/auth/login", method="POST", body={}, expected_status=422),
    test_endpoint("7. Frontend Proxy -> Backend Auth Login (Invalid credentials test)", f"{BASE_FRONTEND}/api/auth/login", method="POST", body={"phone": "9876543210", "password": "WrongPassword"}, expected_status=401),
    test_endpoint("8. Frontend Proxy -> Swagger Docs (/docs)", f"{BASE_FRONTEND}/docs", expected_status=200),
    test_endpoint("9. Frontend Proxy -> OpenAPI Schema (/openapi.json)", f"{BASE_FRONTEND}/openapi.json", expected_status=200),
    test_endpoint("10. Backend Direct Health (/api/health)", f"{BASE_BACKEND}/api/health", expected_status=200),
]

print("="*65)
passed = sum(1 for r in results if r)
total = len(results)
print(f"SUMMARY: {passed}/{total} integration tests passed successfully.")
print("="*65)

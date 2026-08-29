"""
Auth probe: minimal request to Agnes API to validate key before full chat.
"""
import json
import urllib.request
import urllib.error

BASE_URL = "https://api.agnes-ai.cn/v1"
API_KEY = "<REDACTED>"

def auth_probe():
    """Return (status_code, classification, details)"""
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/models",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        code = resp.status
        if code == 200:
            data = json.loads(resp.read())
            return code, "AUTH_PASS", f"Models: {len(data.get('data', []))}"
        else:
            return code, "AUTH_FAILURE", f"Unexpected status: {code}"
    except urllib.error.HTTPError as e:
        return e.code, f"AUTH_{e.code}", e.reason
    except Exception as e:
        return None, "PROVIDER_ERROR", str(e)[:100]

if __name__ == "__main__":
    code, cls, details = auth_probe()
    print(json.dumps({"code": code, "classification": cls, "details": details}, indent=2))

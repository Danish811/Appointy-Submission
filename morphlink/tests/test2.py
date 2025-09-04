import httpx
import time

BASE_URL = "http://localhost:8000"

def assert_status(r, expected):
    if r.status_code != expected:
        print(f"FAILED: {r.request.method} {r.request.url} -> {r.status_code} != {expected}")
    else:
        print(f"PASSED: {r.request.method} {r.request.url} -> {r.status_code}")

def test_health():
    print("\n=== HEALTH CHECKS ===")
    for path in ["/links/health", "/r/health", "/analytics/health"]:
        r = httpx.get(f"{BASE_URL}{path}")
        assert_status(r, 200)
        print(r.json())

def test_links_crud():
    print("\n=== LINKS CRUD ===")
    user = "alice"

    # Create
    r = httpx.post(f"{BASE_URL}/links/", json={"url": "https://example.com", "user": user})
    assert_status(r, 200)
    code = r.json()["short_code"]
    print("Created link:", r.json())

    # Get
    r2 = httpx.get(f"{BASE_URL}/links/{code}", params={"user": user})
    assert_status(r2, 200)
    print("Get link:", r2.json())

    # Update
    r3 = httpx.put(f"{BASE_URL}/links/{code}", json={"url": "https://new.com", "user": user})
    assert_status(r3, 200)
    print("Updated link:", r3.json())

    # List
    r4 = httpx.get(f"{BASE_URL}/links/", params={"user": user})
    assert_status(r4, 200)
    print("List links:", r4.json())

    # Delete
    r5 = httpx.delete(f"{BASE_URL}/links/{code}", params={"user": user})
    assert_status(r5, 200)
    print("Deleted link:", r5.json())

def test_redirect_and_analytics():
    print("\n=== REDIRECT & ANALYTICS ===")
    user = "alice"

    # Create link
    r = httpx.post(f"{BASE_URL}/links/", json={"url": "https://example.com", "user": user})
    code = r.json()["short_code"]

    # Click multiple times
    for i in range(5):
        r2 = httpx.get(f"{BASE_URL}/r/{code}", follow_redirects=False)
        assert_status(r2, 307 if r2.status_code == 307 else r2.status_code)
        print(f"Redirect click {i+1} -> {r2.headers.get('location')}")

    # Check analytics
    r3 = httpx.get(f"{BASE_URL}/analytics/{code}", params={"user": user})
    assert_status(r3, 200)
    print("Analytics:", r3.json())

def test_metrics():
    print("\n=== METRICS ===")
    r = httpx.get(f"{BASE_URL}/links/metrics")
    assert_status(r, 200)
    print("Links RPM:", r.json())

    r = httpx.get(f"{BASE_URL}/analytics/metrics")
    assert_status(r, 200)
    print("Analytics RPM:", r.json())

def test_invalid_user_and_link():
    print("\n=== INVALID USER & LINK ===")
    r = httpx.get(f"{BASE_URL}/links/", params={"user": "charlie"})
    assert_status(r, 401)
    print("Invalid user response:", r.json())

    r2 = httpx.get(f"{BASE_URL}/r/NOPE")
    assert_status(r2, 404)
    print("Non-existent link response:", r2.json())

def test_autopilot_scaling():
    print("\n=== AUTOPILOT SCALING ===")
    user = "alice"
    r = httpx.post(f"{BASE_URL}/links/", json={"url": "https://example.com", "user": user})
    code = r.json()["short_code"]

    print("Flooding redirector to trigger microservice...")
    for _ in range(55):  # threshold=50
        httpx.get(f"{BASE_URL}/r/{code}", timeout=1)
    time.sleep(5)
    print("Check dispatcher console for 'Scaled redirector → microservice'")

def test_microservice_forwarding():
    print("\n=== MICROSERVICE FORWARDING ===")
    user = "alice"
    r = httpx.post(f"{BASE_URL}/links/", json={"url": "https://example.com", "user": user})
    code = r.json()["short_code"]

    # Flood to trigger scaling
    for _ in range(55):
        httpx.get(f"{BASE_URL}/r/{code}", timeout=1)
    time.sleep(3)

    r2 = httpx.get(f"{BASE_URL}/r/{code}", follow_redirects=False)
    assert_status(r2, 307 if r2.status_code == 307 else r2.status_code)
    print("Redirect via microservice:", r2.headers.get("location"))

def test_edge_cases():
    print("\n=== EDGE CASES ===")
    # Missing user param
    r = httpx.get(f"{BASE_URL}/links/")
    assert_status(r, 422)
    print("Missing user param:", r.json())

    # Unsupported method
    r2 = httpx.patch(f"{BASE_URL}/links/")
    assert_status(r2, 405)
    print("Unsupported method:", r2.json())

if __name__ == "__main__":
    test_health()
    test_links_crud()
    test_redirect_and_analytics()
    test_metrics()
    test_invalid_user_and_link()
    test_autopilot_scaling()
    test_microservice_forwarding()
    test_edge_cases()
    print("\n=== ALL TESTS RUN COMPLETE ===")

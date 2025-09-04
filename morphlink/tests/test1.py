import requests

BASE_URL = "http://127.0.0.1:8000"  # monolith mode

USER = "alice"

# --- 1️⃣ Create a new short link --- #
print("Creating a new link...")
response = requests.post(f"{BASE_URL}/links/", params={"url": "https://example.com", "user": USER})
assert response.status_code == 200, response.text
data = response.json()
short_code = data["short_code"]
print(f"Short code created: {short_code}")

# --- 2️⃣ Get link details --- #
print("Getting link details...")
response = requests.get(f"{BASE_URL}/links/{short_code}", params={"user": USER})
assert response.status_code == 200, response.text
print("Link details:", response.json())

# --- 3️⃣ List all links for user --- #
print("Listing all links...")
response = requests.get(f"{BASE_URL}/links/", params={"user": USER})
assert response.status_code == 200, response.text
print("All links:", response.json())

# --- 4️⃣ Update link URL --- #
print("Updating link...")
new_url = "https://example.org"
response = requests.put(f"{BASE_URL}/links/{short_code}", params={"url": new_url, "user": USER})
assert response.status_code == 200, response.text
print("Updated link:", response.json())

# --- 5️⃣ Redirect via Redirector --- #
print("Redirecting...")
response = requests.get(f"{BASE_URL}/r/{short_code}", allow_redirects=False)
assert response.status_code in [302, 307], response.text
redirect_url = response.headers["location"]
print(f"Redirected to: {redirect_url}")

# --- 6️⃣ Check Analytics --- #
print("Checking analytics...")
response = requests.get(f"{BASE_URL}/analytics/", params={"user": USER})
assert response.status_code == 200, response.text
print("Analytics data:", response.json())

# --- 7️⃣ Delete link --- #
print("Deleting link...")
response = requests.delete(f"{BASE_URL}/links/{short_code}", params={"user": USER})
assert response.status_code == 200, response.text
print("Deleted:", response.json())

print("\n✅ All monolith endpoints tested successfully!")

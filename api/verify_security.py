import requests
import random
import time

def verify_security():
    base_url = "http://127.0.0.1:8080/api"
    print("=== Testing Hardened Input Validations ===")
    
    # 1. Test Username too short
    print("1. Testing username too short...")
    resp = requests.post(f"{base_url}/auth/register", json={
        "username": "ab",
        "password": "validpassword"
    })
    print(f"Status: {resp.status_code} (Expected: 422)")
    assert resp.status_code == 422, "Error: Username too short should be blocked with 422!"
    
    # 2. Test Username too long
    print("2. Testing username too long...")
    resp = requests.post(f"{base_url}/auth/register", json={
        "username": "a" * 51,
        "password": "validpassword"
    })
    print(f"Status: {resp.status_code} (Expected: 422)")
    assert resp.status_code == 422, "Error: Username too long should be blocked with 422!"

    # Register a valid user for subsequent tests
    username = f"sec_user_{random.randint(1000, 9999)}"
    print(f"Registering a valid user for testing: {username}")
    resp = requests.post(f"{base_url}/auth/register", json={
        "username": username,
        "password": "validpassword"
    })
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Test Chat message too long
    print("3. Testing chat message too long...")
    resp = requests.post(f"{base_url}/chat", json={
        "message": "Chelsea vs Arsenal " * 50
    }, headers=headers)
    print(f"Status: {resp.status_code} (Expected: 422)")
    assert resp.status_code == 422, "Error: Chat message too long should be blocked with 422!"

    # 4. Test Chat message valid
    print("4. Testing valid chat prediction...")
    resp = requests.post(f"{base_url}/chat", json={
        "message": "Chelsea vs Arsenal"
    }, headers=headers)
    print(f"Status: {resp.status_code} (Expected: 200)")
    assert resp.status_code == 200

    # 5. Test Rate Limiting
    print("5. Testing rate limiting (flooding auth/login endpoint)...")
    success_count = 0
    blocked_count = 0
    
    # Send 15 requests in rapid succession
    for i in range(15):
        resp = requests.post(f"{base_url}/auth/login", json={
            "username": "nonexistentuser", # Skip bcrypt to execute extremely fast
            "password": "anypassword"
        })
        if resp.status_code == 401:
            success_count += 1
        elif resp.status_code == 429:
            blocked_count += 1
            print(f"Request {i+1} blocked: 429 Too Many Requests (Rate limit caught it!)")
        else:
            print(f"Request {i+1} returned status: {resp.status_code}")
            
    print(f"Rate Limiter Results: {success_count} processed, {blocked_count} blocked.")
    assert blocked_count > 0, "Error: Rate limiter did not trigger! Blocked count should be > 0."
    
    print("\n=== SECURITY VERIFICATION PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    verify_security()


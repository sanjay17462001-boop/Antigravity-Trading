"""Final Bigul Connect test — IP confirmed whitelisted."""
import httpx
import pyotp
import json

APP_KEY = "69106af3c87e4bca327b1a377e194ec3"
APP_SECRET = "530f5c7c8b687bea7802a780def6ab9ffc4102f87af80a6db669b645da0b4526"
TOTP_SECRET = "EQAGY5YMMBQBWTKH"
CLIENT_CODE = "DHTR0S06"

otp = pyotp.TOTP(TOTP_SECRET).now()

# Get our IP
ip_resp = httpx.get("https://api.ipify.org?format=json", timeout=10)
print(f"Our IP: {ip_resp.json()['ip']}")
print(f"TOTP: {otp}")
print()

# Test 1: Login with standard headers
print("=" * 50)
print("TEST 1: Login (x-api-key / x-api-secret)")
print("=" * 50)
h = {
    "Content-Type": "application/json",
    "x-api-key": APP_KEY,
    "x-api-secret": APP_SECRET,
}
p = {"source": "B2C", "clientCode": CLIENT_CODE, "totp": otp}
r = httpx.post("https://capi.bigul.co/api/v1/auth/connect/login", json=p, headers=h, timeout=15)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")
print()

# Test 2: Try lowercase header names
print("TEST 2: Login (X-Api-Key / X-Api-Secret)")
h2 = {
    "Content-Type": "application/json",
    "X-Api-Key": APP_KEY,
    "X-Api-Secret": APP_SECRET,
}
r2 = httpx.post("https://capi.bigul.co/api/v1/auth/connect/login", json=p, headers=h2, timeout=15)
print(f"Status: {r2.status_code} | {r2.text[:200]}")
print()

# Test 3: Master CSV without auth
print("TEST 3: Master CSV (no auth)")
r3 = httpx.get("https://capi.bigul.co/masters/NseEquityMaster.csv", timeout=15)
print(f"Status: {r3.status_code} | {r3.text[:200]}")
print()

# Test 4: Master CSV with auth
print("TEST 4: Master CSV (with auth)")
r4 = httpx.get("https://capi.bigul.co/masters/NseEquityMaster.csv", headers=h, timeout=15)
print(f"Status: {r4.status_code} | {r4.text[:200]}")
print()

# Test 5: Check if key/secret are swapped
print("TEST 5: Login (swapped key/secret)")
h5 = {
    "Content-Type": "application/json",
    "x-api-key": APP_SECRET,
    "x-api-secret": APP_KEY,
}
r5 = httpx.post("https://capi.bigul.co/api/v1/auth/connect/login", json=p, headers=h5, timeout=15)
print(f"Status: {r5.status_code} | {r5.text[:200]}")

print("\nDone!")

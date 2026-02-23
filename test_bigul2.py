"""Test Bigul — Connect API + XTS API"""
import httpx
import pyotp

APP_KEY = "69106af3c87e4bca327b1a377e194ec3"
APP_SECRET = "530f5c7c8b687bea7802a780def6ab9ffc4102f87af80a6db669b645da0b4526"
TOTP_SECRET = "EQAGY5YMMBQBWTKH"
PASSWORD = "Bhav@2310"

otp = pyotp.TOTP(TOTP_SECRET).now()
print(f"TOTP: {otp}")

h = {"Content-Type": "application/json", "x-api-key": APP_KEY, "x-api-secret": APP_SECRET}

# Connect API — different client codes
for code in ["DHTR0S06", "TRS06"]:
    otp = pyotp.TOTP(TOTP_SECRET).now()
    p = {"source": "B2C", "clientCode": code, "totp": otp, "password": PASSWORD}
    r = httpx.post("https://capi.bigul.co/api/v1/auth/connect/login", json=p, headers=h, timeout=15)
    print(f"Connect clientCode={code}: {r.status_code} | {r.text[:250]}")

print()

# XTS Market Data login
print("=== XTS Market Data Login ===")
xts_p = {"secretKey": "Jris751$4o", "appKey": "809e40a370b0c3c83d3710", "source": "WebAPI"}
r = httpx.post("https://trading.bigul.co/apimarketdata/auth/login", json=xts_p, timeout=15)
print(f"Status: {r.status_code} | {r.text[:300]}")

print()

# XTS Interactive login
print("=== XTS Interactive Login ===")
xts_i = {"secretKey": "Jris751$4o", "appKey": "809e40a370b0c3c83d3710", "source": "WebAPI"}
r2 = httpx.post("https://trading.bigul.co/interactive/user/session", json=xts_i, timeout=15)
print(f"Status: {r2.status_code} | {r2.text[:300]}")

print("\nDone!")

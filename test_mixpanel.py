#!/usr/bin/env python3
"""
Test script for Mixpanel integration - Testing both US and EU regions
Run: python test_mixpanel.py
"""

import os
import json
import base64
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_endpoint(endpoint_name, track_url, engage_url, token, user_id):
    print(f"\n{'='*60}")
    print(f"Testing {endpoint_name} Endpoint")
    print(f"{'='*60}")

    # Test 1: Track event
    print("\n1️⃣ Tracking event...")
    event_data = {
        "event": f"{endpoint_name} Test Event",
        "properties": {
            "distinct_id": user_id,
            "token": token,
            "time": int(time.time()),
            "region": endpoint_name,
            "test_property": "test_value"
        }
    }

    data_str = json.dumps([event_data])
    data_b64 = base64.b64encode(data_str.encode()).decode()

    response = requests.get(
        track_url,
        params={"data": data_b64, "verbose": 1},
        timeout=10
    )

    print(f"   Response: {response.status_code}")
    print(f"   Body: {response.text}")

    # Test 2: Set user profile
    print("\n2️⃣ Setting user profile...")
    profile_data = {
        "$token": token,
        "$distinct_id": user_id,
        "$set": {
            "$name": f"{endpoint_name} Test User",
            "region": endpoint_name,
            "test_mode": True
        }
    }

    data_str = json.dumps([profile_data])
    data_b64 = base64.b64encode(data_str.encode()).decode()

    response = requests.get(
        engage_url,
        params={"data": data_b64, "verbose": 1},
        timeout=10
    )

    print(f"   Response: {response.status_code}")
    print(f"   Body: {response.text}")

def main():
    print("🧪 Testing Mixpanel Integration - US vs EU Endpoints\n")

    MIXPANEL_TOKEN = os.getenv("MIXPANEL_TOKEN")

    if not MIXPANEL_TOKEN:
        print("❌ MIXPANEL_TOKEN not found in .env")
        return

    print(f"✅ Using token: {MIXPANEL_TOKEN}\n")

    test_user_id = f"test_user_{int(time.time())}"

    # Test US endpoint
    test_endpoint(
        "US",
        "https://api.mixpanel.com/track",
        "https://api.mixpanel.com/engage",
        MIXPANEL_TOKEN,
        test_user_id
    )

    # Test EU endpoint
    test_endpoint(
        "EU",
        "https://api-eu.mixpanel.com/track",
        "https://api-eu.mixpanel.com/engage",
        MIXPANEL_TOKEN,
        test_user_id
    )

    print(f"\n{'='*60}")
    print("✅ All tests completed!")
    print(f"{'='*60}")
    print(f"\n📊 Check your Mixpanel dashboard at: https://mixpanel.com/report/")
    print(f"   Look for events from user: {test_user_id}")
    print(f"\n🔍 If both show status:1 but no events appear:")
    print(f"   1. Wrong project token (check Project Settings)")
    print(f"   2. Events may take 1-2 minutes to appear")
    print(f"   3. Check time filter in dashboard (set to 'Last 30 days')")

if __name__ == "__main__":
    main()

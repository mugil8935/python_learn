import requests
import json
import os
import csv
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AUTH_URL = "https://sabarimalaonline.org/api/tof/authenticateEntry"
MASTER_URL = "https://sabarimalaonline.org/api/master/getMasterList"
TOKEN_FILE = "token_cache.json"
CREDENTIALS_FILE = "credentials.json"
OUTPUT_CSV = "pilgrims.csv"


# ------------------ TOKEN HANDLING ------------------

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ credentials.json not found.")
        return []
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_tokens(tokens):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)


def is_token_valid(token_info):
    if not token_info:
        return False
    ts = datetime.fromisoformat(token_info["timestamp"])
    return datetime.now() - ts < timedelta(hours=1)


def get_token(username, password, tokens):
    """Fetch new token if expired or missing"""
    if username in tokens and is_token_valid(tokens[username]):
        print(f"✅ Using cached token for {username}")
        return tokens[username]["token"]

    print(f"🔄 Fetching new token for {username}")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"username": username, "password": password}

    try:
        r = requests.post(AUTH_URL, data=data, headers=headers, verify=False, timeout=15)
        r.raise_for_status()
        token = r.headers.get("tof-auth-token")

        if not token:
            print(f"⚠️ No 'tof-auth-token' in response for {username}")
            return None

        tokens[username] = {
            "token": token,
            "timestamp": datetime.now().isoformat()
        }
        save_tokens(tokens)
        print(f"💾 Saved new token for {username}")
        return token

    except requests.RequestException as e:
        print(f"❌ Auth request failed for {username}: {e}")
        return None


# ------------------ MASTER LIST FETCH ------------------

def get_master_list(username, token):
    headers = {
        "Content-Type": "application/json",
        "tof-auth-token": token
    }
    payload = {"imageFlag": True}

    try:
        r = requests.post(MASTER_URL, json=payload, headers=headers, verify=False, timeout=30)
        r.raise_for_status()
        data = r.json()

        # ✅ The response contains "masterListDetailsModel" list
        if isinstance(data, dict) and "masterListDetailsModel" in data:
            return data["masterListDetailsModel"]
        else:
            print(f"⚠️ Unexpected response structure for {username}")
            return []

    except requests.RequestException as e:
        print(f"❌ Master list request failed for {username}: {e}")
        return []


# ------------------ CSV SAVE ------------------

def save_to_csv(data_rows):
    """Write all rows into CSV (overwrite old file each run)"""
    fieldnames = [
        "username",
        "pilgrimId",
        "firstName",
        "lastName",
        "mobileNumber",
        "idProofType",
        "idProofName",
        "idProofNumber"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data_rows:
            writer.writerow(row)
    print(f"💾 Saved {len(data_rows)} records to {OUTPUT_CSV}")


# ------------------ MAIN FLOW ------------------

def main():
    credentials = load_credentials()
    tokens = load_tokens()
    all_rows = []

    for cred in credentials:
        username = cred["username"]
        password = cred["password"]

        token = get_token(username, password, tokens)
        if not token:
            continue

        master_list = get_master_list(username, token)
        print(f"📦 {username} → {len(master_list)} records fetched")

        for item in master_list:
            row = {
                "username": username,
                "pilgrimId": item.get("pilgrimId", ""),
                "firstName": item.get("firstName", ""),
                "lastName": item.get("lastName", ""),
                "mobileNumber": item.get("mobileNumber", ""),
                "idProofType": item.get("idProofType", ""),
                "idProofName": item.get("idProofName", ""),
                "idProofNumber": item.get("idProofNumber", "")
            }
            all_rows.append(row)

    if all_rows:
        save_to_csv(all_rows)
    else:
        print("⚠️ No data to save.")


if __name__ == "__main__":
    main()
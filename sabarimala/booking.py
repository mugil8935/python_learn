import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AUTH_URL = "https://sabarimalaonline.org/api/tof/authenticateEntry"
MASTER_URL = "https://sabarimalaonline.org/api/master/getMasterList"
ADD_TO_WISHLIST_URL = "https://sabarimalaonline.org/api/tofcart/addToWishlist"
CART_TRANSACTION_URL = "https://sabarimalaonline.org/api/tofcart/cartTransaction"

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token_cache.json"
BOOK_FILE = "book.json"
EXCEL_FILE = "SasthaGroup 2025.xlsx"


# ------------------ TOKEN HANDLING ------------------

def load_credentials():
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
    return datetime.now() - ts < timedelta(minutes=15)


def get_token(username, password, tokens):
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
        resp_json = {}
        try:
            resp_json = r.json()
        except Exception:
            pass
        user_id = resp_json.get("userId") or resp_json.get("userDetails", {}).get("userId")
        if not token:
            print(f"⚠️ No 'tof-auth-token' in response for {username}")
            return None
        tokens[username] = {
            "token": token,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        }
        save_tokens(tokens)
        print(f"💾 Saved new token for {username} (userId={user_id})")
        return token
    except requests.RequestException as e:
        print(f"❌ Auth request failed for {username}: {e}")
        return None


def get_userid(username, tokens):
    if username in tokens and is_token_valid(tokens[username]):
        return tokens[username].get("user_id")
    return None


# ------------------ MASTER LIST ------------------

def get_master_list(username, token):
    headers = {"Content-Type": "application/json", "tof-auth-token": token}
    payload = {"imageFlag": True}
    try:
        r = requests.post(MASTER_URL, json=payload, headers=headers, verify=False, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "masterListDetailsModel" in data:
            return data["masterListDetailsModel"]
        else:
            print(f"⚠️ Unexpected response structure for {username}")
            return []
    except requests.RequestException as e:
        print(f"❌ Master list request failed for {username}: {e}")
        return []


# ------------------ BOOKING JSON ------------------

def build_booking_json(pilgrim, user_id, route):
      # determine slot based on route
    if str(route).strip().lower() == "siruvali":
        slot_name = "11:00 - 12:00"
        slot_id = 8
    elif str(route).strip().lower() == "peruvali":
        slot_name = "06:00 - 07:00"
        slot_id = 3
    else:
        slot_name = "06:00 - 07:00"  # default
        slot_id = 3
    return {
        "darshanBookingModel": {
            "bookingSelfOther": "group",
            "darshanDate": "05-Dec-2025",
            "reportingMasterId": "2",
            "channelTypeId": 100001,
            "darshanTypeId": 100001,
            "slotId": slot_id,
            "slotName": slot_name,
            "noOfPersons": 1,
            "ticketPriceTotal": 0,
            "userId": user_id,
            "serviceTypeId": "100001",
            "darshanBookingPilgrimList": [
                {
                    "pilgrimMasterId": pilgrim.get("pilgrimId"),
                    "firstName": pilgrim.get("firstName", ""),
                    "lastName": pilgrim.get("lastName", ""),
                    "dateOfBirth": pilgrim.get("dob", ""),
                    "mobileNumber": pilgrim.get("mobileNumber", ""),
                    "gender": pilgrim.get("gender", "Male"),
                    "idProofType": pilgrim.get("idProofType", ""),
                    "idProofNumber": pilgrim.get("idProofNumber", ""),
                    "addressLine1": pilgrim.get("addressLine1", ""),
                    "addressLine2": pilgrim.get("addressLine2", ""),
                    "city": pilgrim.get("city", ""),
                    "state": pilgrim.get("state", ""),
                    "country": pilgrim.get("country", "India"),
                    "pincode": "636102",
                    "image": pilgrim.get("imagePath", ""),
                    "newImage": None,
                    "registrationStatus": "N",
                    "baliTharpanam": ""
                }
            ],
            "prasadamBookingList": []
        },
        "pilgrimWelfareDetailsModel": {"totalWelfareAmount": 0}
    }


# ------------------ MAIN ------------------

def main():
    with open(BOOK_FILE, "r", encoding="utf-8") as f:
        book_data = json.load(f)
    usernames = book_data.get("usernames", [])

    credentials = {c["username"]: c["password"] for c in load_credentials()}
    tokens = load_tokens()

    df = pd.read_excel(EXCEL_FILE, sheet_name="working_copy")

    for username in usernames:
        if username not in credentials:
            print(f"⚠️ Username {username} not found in credentials.json, skipping.")
            continue

        token = get_token(username, credentials[username], tokens)
        if not token:
            continue

        user_id = get_userid(username, tokens)
        master_list = get_master_list(username, token)
        if not master_list:
            continue
        df["Username"] = df["Username"].astype(str).str.strip()
        df["booking_status"] = df["booking_status"].astype(str).str.strip().str.lower()
        # Filter only matching username + ready for processing
        # &
            # (df["booking_status"].str.contains("ready", case=False, na=False))
        print("🧩 Unique booking_status values:", df["booking_status"].unique().tolist())
        for i, val in enumerate(df["booking_status"]):
            print(f"{i}: {repr(val)}")
            print(val == 'ready')
        filtered_rows = df[
            (df["booking_status"] == 'ready')
        ]
        if filtered_rows.empty:
           print(f"⚠️ No ready rows found for username {username}")
           continue
        filtered_rows = df[
            (df["Username"] == str(username).strip()) 
        ]

        if filtered_rows.empty:
            print(f"⚠️ No ready rows found for username {username}")
            continue

        for idx, row in filtered_rows.iterrows():
            pilgrim_id_excel = str(row["Pilgrim ID"]).strip()
            route = str(row.get("Route", "")).strip()

            matched = next(
                (p for p in master_list if str(p.get("pilgrimId")) == pilgrim_id_excel),
                None
            )
            if not matched:
                print(f"❌ No pilgrim match for {username} → Pilgrim ID {pilgrim_id_excel}")
                continue

            booking_json = build_booking_json(matched, user_id, route)

            # ------------------ CALL 1: addToWishlist ------------------
            headers = {"Content-Type": "application/json", "tof-auth-token": token}
            try:
                resp1 = requests.post(
                    "https://sabarimalaonline.org/api/tofcart/addToWishlist",
                    json=booking_json, headers=headers, verify=False, timeout=30
                )
                resp1.raise_for_status()
                wishlist_response = resp1.json()
                print(f"🛒 addToWishlist → username={username} pilgrimId={pilgrim_id_excel} → {wishlist_response}")
            except Exception as e:
                print(f"❌ addToWishlist failed for {username}, pilgrim {pilgrim_id_excel}: {e}")
                continue

            cart_id = wishlist_response.get("cartId")
            booking_id = wishlist_response.get("bookingId")

            # update dataframe
            df.loc[idx, "cartId"] = cart_id
            df.loc[idx, "bookingId"] = booking_id

            if not cart_id:
                print(f"⚠️ No cartId returned for {username} pilgrim {pilgrim_id_excel}")
                continue

            # ------------------ CALL 2: cartTransaction ------------------
            txn_payload = {"cartId": int(cart_id)}
            try:
                resp2 = requests.post(
                    "https://sabarimalaonline.org/api/tofcart/cartTransaction",
                    json=txn_payload, headers=headers, verify=False, timeout=30
                )
                resp2.raise_for_status()
                txn_response = resp2.json()
                print(f"💳 cartTransaction → username={username} cartId={cart_id} → {txn_response}")
            except Exception as e:
                print(f"❌ cartTransaction failed for {username} cartId={cart_id}: {e}")

    # ------------------ Save Updated Excel ------------------
    with pd.ExcelWriter(EXCEL_FILE, mode="a", if_sheet_exists="replace", engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="working_copy", index=False)

    print(f"💾 Excel updated successfully with cartId and bookingId.")

if __name__ == "__main__":
    main()
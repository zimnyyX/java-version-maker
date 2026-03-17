import requests
import time
import minecraft_launcher_lib
import json
import os

def get_device_code(client_id):
    url = "https://login.live.com/oauth20_connect.srf"
    data = {
        "client_id": client_id,
        "scope": "XboxLive.signin offline_access",
        "response_type": "device_code"
    }
    try:
        response = requests.post(url, data=data, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Status {response.status_code}: {response.text}")
        return response.json()
    except Exception as e:
        msg = str(e) if str(e) else f"Unknown error ({type(e).__name__})"
        raise Exception(f"Failed to get device code: {msg}")

def complete_device_code_login(client_id, device_code_data):
    url = "https://login.live.com/oauth20_token.srf"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code_data["device_code"]
    }

    interval = device_code_data.get("interval", 5)
    expires_in = device_code_data.get("expires_in", 900)
    start_time = time.time()

    while time.time() - start_time < expires_in:
        try:
            response = requests.post(url, data=data)
            res_data = response.json()

            if "access_token" in res_data:
                return _authenticate_minecraft(client_id, res_data["access_token"], res_data.get("refresh_token"))

            error = res_data.get("error")
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            elif error:
                error_msg = res_data.get("error_description", error)
                raise Exception(error_msg if error_msg else f"Unknown token error: {error}")
        except Exception as e:
            if "authorization_pending" not in str(e):
                msg = str(e) if str(e) else f"Unknown login error ({type(e).__name__})"
                raise Exception(f"Login error: {msg}")

        time.sleep(interval)

    raise Exception("Login timed out. Please try again.")

def _authenticate_minecraft(client_id, ms_token, refresh_token):
    try:
        # XBL
        xbl_request = minecraft_launcher_lib.microsoft_account.authenticate_with_xbl(ms_token)
        if "Token" not in xbl_request:
            raise Exception("Xbox Live authentication failed.")

        xbl_token = xbl_request["Token"]
        userhash = xbl_request["DisplayClaims"]["xui"][0]["uhs"]

        # XSTS
        xsts_request = minecraft_launcher_lib.microsoft_account.authenticate_with_xsts(xbl_token)
        if "Token" not in xsts_request:
            raise Exception("XSTS authentication failed. Ensure you have an Xbox profile.")

        xsts_token = xsts_request["Token"]

        # Minecraft
        account_request = minecraft_launcher_lib.microsoft_account.authenticate_with_minecraft(userhash, xsts_token)
        if "access_token" not in account_request:
            raise Exception("Minecraft authentication failed.")

        mc_access_token = account_request["access_token"]

        # Profile
        profile = minecraft_launcher_lib.microsoft_account.get_profile(mc_access_token)
        if not profile:
            raise Exception("Received empty profile from Minecraft services.")

        if "error" in profile:
            if profile["error"] == "NOT_FOUND":
                raise Exception("This Microsoft account does not own Minecraft.")
            else:
                error_name = profile.get("error", "Unknown")
                error_msg = profile.get("errorMessage", error_name)
                raise Exception(f"Failed to get Minecraft profile: {error_msg}")

        profile["access_token"] = mc_access_token
        profile["refresh_token"] = refresh_token

        return profile
    except Exception as e:
        raise Exception(f"Minecraft Auth Error: {str(e)}")

def save_session(mc_dir, auth_data):
    session_path = os.path.join(mc_dir, "session.json")
    with open(session_path, "w") as f:
        json.dump(auth_data, f)

def load_session(mc_dir):
    session_path = os.path.join(mc_dir, "session.json")
    if os.path.exists(session_path):
        try:
            with open(session_path, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def refresh_session(client_id, refresh_token):
    try:
        # minecraft-launcher-lib has complete_refresh but it might have similar issues
        # or we might want to stay consistent with our manual flow if needed.
        # Actually, let's try to use the library's one first.
        return minecraft_launcher_lib.microsoft_account.complete_refresh(client_id, None, None, refresh_token)
    except Exception as e:
        raise Exception(f"Failed to refresh session: {str(e)}")

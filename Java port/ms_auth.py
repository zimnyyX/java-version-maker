import requests
import time
import minecraft_launcher_lib
from typing import cast

def get_device_code(client_id):
    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
    data = {
        "client_id": client_id,
        "scope": "XboxLive.signin offline_access"
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()

def complete_device_code_login(client_id, device_code_data):
    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code_data["device_code"]
    }

    interval = device_code_data.get("interval", 5)
    expires_in = device_code_data.get("expires_in", 900)
    start_time = time.time()

    while time.time() - start_time < expires_in:
        response = requests.post(url, data=data)
        res_data = response.json()

        if "access_token" in res_data:
            # Step 1: MS Access Token
            ms_token = res_data["access_token"]
            refresh_token = res_data.get("refresh_token")

            # Step 2: XBL
            xbl_request = minecraft_launcher_lib.microsoft_account.authenticate_with_xbl(ms_token)
            xbl_token = xbl_request["Token"]
            userhash = xbl_request["DisplayClaims"]["xui"][0]["uhs"]

            # Step 3: XSTS
            xsts_request = minecraft_launcher_lib.microsoft_account.authenticate_with_xsts(xbl_token)
            xsts_token = xsts_request["Token"]

            # Step 4: Minecraft
            account_request = minecraft_launcher_lib.microsoft_account.authenticate_with_minecraft(userhash, xsts_token)
            if "access_token" not in account_request:
                raise Exception("Minecraft authentication failed")

            mc_access_token = account_request["access_token"]

            # Step 5: Profile
            profile = minecraft_launcher_lib.microsoft_account.get_profile(mc_access_token)
            if "error" in profile and profile["error"] == "NOT_FOUND":
                raise Exception("Account does not own Minecraft")

            profile["access_token"] = mc_access_token
            profile["refresh_token"] = refresh_token

            return profile

        if res_data.get("error") != "authorization_pending":
            raise Exception(res_data.get("error_description", res_data.get("error")))

        time.sleep(interval)

    raise Exception("Login timed out")

import requests
import random
import secrets
import base64
import json
from flask import Flask, jsonify, request
from datetime import datetime, timedelta, timezone

# ------------------------------
# Configuration
# ------------------------------
class GameInfo():
    def __init__(self):
        self.TitleId: str = "FE314"
        self.SecretKey: str = "WUSAOXAYS9TKAANYF3N77JFEJYD6N571JHEUN83NKHWBH3DFD4"
        self.ApiKey: str = "OC|1243808488818929|a88a73bc8d73237018c75eee39f5bb48"
        self.Webhook: str = "https://discord.com/api/webhooks/1535218499000074262/rFKlM4fMEM6ILyb07jSElKCHK8ZHVDtbX7xXAswVlpVJaXDhMcugvCrU-IfJON3NX-M1"   # <-- set your webhook

    def GetAuthHeaders(self) -> dict:
        return {
            "content-type": "application/json",
            "X-SecretKey": self.SecretKey
        }

    def GetTitle(self) -> str:
        return self.TitleId


settings = GameInfo()
app = Flask(__name__)

# In‑memory caches (will reset on each Vercel invocation)
playfabCache = {}
muteCache = {}
currentDailyItems = []
lastUpdateDate = None
webhookSentToday = False

BAD_WORDS = {
    "KKK", "PENIS", "NIGG", "NEG", "NIGA", "MONKEYSLAVE", "SLAVE", "FAG",
    "NAGGI", "TRANNY", "QUEER", "KYS", "DICK", "PUSSY", "VAGINA", "BIGBLACKCOCK",
    "DILDO", "HITLER", "KKX", "XKK", "NIGE", "NIG", "NI6", "PORN",
    "JEW", "JAXX", "TTTPIG", "SEX", "COCK", "CUM", "FUCK", "ELLIOT",
    "JMAN", "K9", "NIGGA", "NICKER", "NICKA", "REEL", "NII", "@here",
    "!", " ", "PPPTIG", "CLEANINGBOT", "JANITOR", "H4PKY", "MOSA",
    "NIGGER", "IHATENIGGERS", "@everyone", "BEANER", "B3ANER", "BEAN3R",
    "B3AN3R", "TTT"
}

# List of item IDs – replace with real ones
DailyTees = [
    "LBAAE.",
    "LSAAL.",
    "SPIDERMONKEBUNDL",
    "LFAAV.",
    "Item5",
    "Item6",
    "Item7",
    "Item8",
    "Item9"
]

# ------------------------------
# Helper: Webhook
# ------------------------------
def sendwebhook(title, desc, fields, color=65280):
    try:
        embed = {
            "embeds": [{
                "title": title,
                "description": desc,
                "color": color,
                "fields": fields or []
            }]
        }
        requests.post(settings.Webhook, json=embed)
    except Exception as e:
        print(f"Webhook error: {e}")

def send_discord_webhook(msg):
    webhook_url = "https://discord.com/api/webhooks/1535218499000074262/rFKlM4fMEM6ILyb07jSElKCHK8ZHVDtbX7xXAswVlpVJaXDhMcugvCrU-IfJON3NX-M1"
    response = requests.post(webhook_url, json={"content": msg})
    return response.status_code == 204

# ------------------------------
# Helper: Daily items
# ------------------------------
def getDailyItems():
    global currentDailyItems, lastUpdateDate, webhookSentToday
    today = datetime.utcnow().date().isoformat()

    if lastUpdateDate != today or len(currentDailyItems) == 0:
        shuffled = DailyTees.copy()
        random.shuffle(shuffled)
        selected = shuffled[:3]

        while len(selected) < 3:
            selected.append(random.choice(DailyTees))

        currentDailyItems = selected
        lastUpdateDate = today
        webhookSentToday = False

    return currentDailyItems

def sendDailyWebhookIfNeeded():
    global webhookSentToday, lastUpdateDate
    today = datetime.utcnow().date().isoformat()
    items = getDailyItems()

    if not webhookSentToday or lastUpdateDate != today:
        sendwebhook(
            "Daily Tee Updated 😻",
            "New daily cosmetics have been selected!",
            [
                {"name": "CosmeticStand1", "value": items[0] or "Not set", "inline": True},
                {"name": "CosmeticStand2", "value": items[1] or "Not set", "inline": True},
                {"name": "CosmeticStand3", "value": items[2] or "Not set", "inline": True},
                {"name": "Date", "value": datetime.utcnow().strftime("%Y-%m-%d"), "inline": False}
            ],
            65280
        )
        webhookSentToday = True

def generateTOTD():
    items = getDailyItems()
    now = datetime.utcnow().isoformat() + "Z"
    later = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    return json.dumps([
        {
            "PedestalID": "CosmeticStand1",
            "ItemName": items[0] or DailyTees[0],
            "StartTimeUTC": now,
            "EndTimeUTC": later
        },
        {
            "PedestalID": "CosmeticStand2",
            "ItemName": items[1] or DailyTees[1],
            "StartTimeUTC": now,
            "EndTimeUTC": later
        },
        {
            "PedestalID": "CosmeticStand3",
            "ItemName": items[2] or DailyTees[2],
            "StartTimeUTC": now,
            "EndTimeUTC": later
        }
    ])

# ------------------------------
# Helper: Nonce validation
# ------------------------------
def validateNonce(nonce, oculusId):
    try:
        resp = requests.post(
            f"https://graph.oculus.com/user_nonce_validate?nonce={nonce}&user_id={oculusId}&access_token={settings.ApiKey}",
            headers={"content-type": "application/json"}
        )
        return resp.json().get("is_valid", False)
    except Exception as e:
        print(f"Nonce validation error: {e}")
        return False

# ------------------------------
# Helper: PlayFab CloudScript
# ------------------------------
def returnFunctionJson(data, funcname, funcparam=None):
    if funcparam is None:
        funcparam = {}
    # Extract UserId from the request data
    rjson = data.get("FunctionParameter", {})
    userId = rjson.get("CallerEntityProfile", {}).get("Lineage", {}).get("TitlePlayerAccountId")

    if not userId:
        # fallback – try to get from top level if present
        userId = data.get("PlayFabId") or data.get("CallerEntityProfile", {}).get("Lineage", {}).get("TitlePlayerAccountId")

    req = requests.post(
        f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": userId,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers=settings.GetAuthHeaders()
    )
    if req.status_code == 200:
        result = req.json().get("data", {}).get("FunctionResult", {})
        return jsonify(result), req.status_code
    else:
        return jsonify({}), req.status_code

# ------------------------------
# Existing helper (kept for compatibility)
# ------------------------------
def GetIsNonceValid(nonce, oculusId):
    return validateNonce(nonce, oculusId)

def VerifyOculusStandards(userId, nonce):
    # Keep the original implementation if needed, but we'll use validateNonce for simplicity
    return {"is_valid": validateNonce(nonce, userId), "org_scoped_id": None}

# ------------------------------
# Attestation endpoints (existing)
# ------------------------------
@app.route("/api/authenticate/attestation/getNonce", methods=["POST"])
def GetNonce():
    data = request.get_json()
    user_id = data.get("UserId")
    nonce = data.get("Nonce")
    if not user_id or not nonce:
        return jsonify({"error": "Missing parameters"}), 400
    verification = VerifyOculusStandards(user_id, nonce)
    if not verification["is_valid"]:
        return jsonify({"error": "Invalid user info"}), 403
    challengeNonce = secrets.token_urlsafe(16)
    # currentNonces is not defined – we'll store in a global dict
    global currentNonces
    if 'currentNonces' not in globals():
        currentNonces = {}
    currentNonces[user_id] = challengeNonce
    return jsonify({
        "challenge_nonce": challengeNonce,
        "org_scoped_id": verification.get("org_scoped_id")
    })

# (MotherShipAuth endpoint is kept as is from the original file)

# ------------------------------
# Modified: PlayFab Authentication
# ------------------------------
@app.route("/api/PlayFabAuthentication", methods=["POST"])
def playfabauthentication():
    rjson = request.get_json()

    # --- Required fields ---
    if rjson.get("CustomId") is None:
        return jsonify({"Message": "Missing CustomId parameter", "Error": "BadRequest-NoCustomId"}), 400
    if rjson.get("Nonce") is None:
        return jsonify({"Message": "Missing Nonce parameter", "Error": "BadRequest-NoNonce"}), 400
    if rjson.get("AppId") is None:
        return jsonify({"Message": "Missing AppId parameter", "Error": "BadRequest-NoAppId"}), 400
    if rjson.get("Platform") is None:
        return jsonify({"Message": "Missing Platform parameter", "Error": "BadRequest-NoPlatform"}), 400
    if rjson.get("OculusId") is None:
        return jsonify({"Message": "Missing OculusId parameter", "Error": "BadRequest-NoOculusId"}), 400

    # --- AppId & CustomId checks ---
    if rjson.get("AppId") != settings.TitleId:
        return jsonify({"Message": "Request sent for the wrong App ID", "Error": "BadRequest-AppIdMismatch"}), 400
    if not rjson.get("CustomId").startswith("OC") and not rjson.get("CustomId").startswith("PI"):
        return jsonify({"Message": "Bad request", "Error": "BadRequest-No OC or PI Prefix"}), 400

    nonce = rjson.get("Nonce")
    oculusId = rjson.get("OculusId")

    validation_result = VerifyOculusStandards(oculusId, nonce)
    if validation_result.get("is_valid") == True:
        send_discord_webhook("yay auth with playfab!!!" + f" OculusId: {oculusId}, Nonce: {nonce}")
    else:
        send_discord_webhook("no auth with playfab!?!" + f" OculusId: {oculusId}, Nonce: {nonce}")
        return jsonify({"Message":"No authentication with Oculus","Error":"BadRequest-NoOculusAuth"})

    # --- Login with PlayFab ---
    url = f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId"
    login_request = requests.post(
        url=url,
        json={
            "ServerCustomId": rjson.get("CustomId"),
            "CreateAccount": True
        },
        headers=settings.GetAuthHeaders()
    )

    if login_request.status_code == 200:
        data = login_request.json().get("data")
        sessionTicket = data.get("SessionTicket")
        entityToken = data.get("EntityToken").get("EntityToken")
        playFabId = data.get("PlayFabId")
        entityType = data.get("EntityToken").get("Entity").get("Type")
        entityId = data.get("EntityToken").get("Entity").get("Id")

        # Link Custom ID
        link_resp = requests.post(
            f"https://{settings.TitleId}.playfabapi.com/Client/LinkCustomID",
            json={
                "ForceLink": True,
                "CustomId": rjson.get("CustomId")
            },
            headers={
                "X-Authorization": sessionTicket,
                "Content-Type": "application/json"
            }
        )
        print("LinkCustomID response:", link_resp.json())

        # Success webhook
        sendwebhook(
            "PlayFab Authentication Successful 😻",
            "User successfully authenticated",
            [
                {"name": "OculusId", "value": oculusId, "inline": True},
                {"name": "PlayFabId", "value": playFabId, "inline": True},
                {"name": "EntityId", "value": entityId, "inline": False}
            ],
            65280
        )

        return jsonify({
            "PlayFabId": playFabId,
            "SessionTicket": sessionTicket,
            "EntityToken": entityToken,
            "EntityId": entityId,
            "EntityType": entityType
        })
    else:
        # Handle bans and other errors
        if login_request.status_code == 403:
            ban_info = login_request.json()
            if ban_info.get('errorCode') == 1002:
                ban_message = ban_info.get('errorMessage', "No ban message provided.")
                ban_details = ban_info.get('errorDetails', {})
                ban_expiration_key = next(iter(ban_details.keys()), None)
                ban_expiration_list = ban_details.get(ban_expiration_key, [])
                ban_expiration = ban_expiration_list[0] if ban_expiration_list else "Indefinite"

                sendwebhook(
                    "PlayFab Authentication - User Banned",
                    f"User {oculusId} attempted to authenticate but is banned",
                    [
                        {"name": "OculusId", "value": oculusId, "inline": True},
                        {"name": "Ban Expiration", "value": ban_expiration, "inline": True},
                        {"name": "Ban Message", "value": ban_message, "inline": False}
                    ],
                    16711680
                )

                return jsonify({
                    "BanMessage": ban_expiration_key,
                    "BanExpirationTime": ban_expiration
                }), 403
            else:
                error_message = ban_info.get('errorMessage', 'Forbidden without ban information.')
                return jsonify({
                    "Error": "PlayFab Error",
                    "Message": error_message
                }), 403
        else:
            error_info = login_request.json()
            error_message = error_info.get('errorMessage', 'An error occurred.')
            sendwebhook(
                "PlayFab Authentication Failed",
                "Authentication error occurred",
                [
                    {"name": "OculusId", "value": oculusId, "inline": True},
                    {"name": "Status Code", "value": login_request.status_code, "inline": True},
                    {"name": "Error", "value": error_message, "inline": False}
                ],
                16711680
            )
            return jsonify({
                "Error": "PlayFab Error",
                "Message": error_message
            }), login_request.status_code

# ------------------------------
# Modified: Title Data (with TOTD)
# ------------------------------
@app.route("/api/TitleData", methods=["POST"])
@app.route("/v1/title-data/client", methods=["POST"])
@app.route("/api/TD", methods=["POST"])
def titled_data():
    sendDailyWebhookIfNeeded()
    totd = generateTOTD()
    # Return only the TOTD and an empty MOTD
    return jsonify({
        "MOTD": "WECOME TO BURN TAG\nUPD <||>  2024 ILAVA YOU\nFOUNDERS <||> OMIFY / DAVEEPLAYS\nHAVE A GOOD DAY AND GO MAKE SOME FRIENDS\n\n<|> discord.gg/4XPue2Kuht <|>",
        "TOTD": totd
    })

# ------------------------------
# Modified: Photon Authentication (simplified)
# ------------------------------
@app.route("/api/photon", methods=["POST"])
def photonauth():
    print(f"Received {request.method} request at /api/photon")
    getjson = request.get_json()
    Ticket = getjson.get("Ticket")
    Nonce = getjson.get("Nonce")
    Platform = getjson.get("Platform")
    UserId = getjson.get("UserId")
    nickName = getjson.get("username")
    if request.method.upper() == "GET":
        rjson = request.get_json()
        print(f"{request.method} : {rjson}")

        userId = Ticket.split('-')[0] if Ticket else None
        print(f"Extracted userId: {UserId}")

        if userId is None or len(userId) != 16:
            print("Invalid userId")
            return jsonify({
                'resultCode': 2,
                'message': 'Invalid token',
                'userId': None,
                'nickname': None
            })

        if Platform != 'Quest':
            return jsonify({'Error': 'Bad request', 'Message': 'Invalid platform!'}),403

        if Nonce is None:
            return jsonify({'Error': 'Bad request', 'Message': 'Not Authenticated!'}),304

        req = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/GetUserAccountInfo",
            json={"PlayFabId": userId},
            headers={
                "content-type": "application/json",
                "X-SecretKey": secretkey
            })

        print(f"Request to PlayFab returned status code: {req.status_code}")

        if req.status_code == 200:
            nickName = req.json().get("UserInfo",
                                      {}).get("UserAccountInfo",
                                              {}).get("Username")
            if not nickName:
                nickName = None

            print(
                f"Authenticated user {userId.lower()} with nickname: {nickName}"
            )

            return jsonify({
                'resultCode': 1,
                'message':
                f'Authenticated user {userId.lower()} title {settings.TitleId.lower()}',
                'userId': f'{userId.upper()}',
                'nickname': nickName
            })
        else:
            print("Failed to get user account info from PlayFab")
            return jsonify({
                'resultCode': 0,
                'message': "Something went wrong",
                'userId': None,
                'nickname': None
            })

    elif request.method.upper() == "POST":
        rjson = request.get_json()
        print(f"{request.method} : {rjson}")

        ticket = rjson.get("Ticket")
        userId = ticket.split('-')[0] if ticket else None
        print(f"Extracted userId: {userId}")

        if userId is None or len(userId) != 16:
            print("Invalid userId")
            return jsonify({
                'resultCode': 2,
                'message': 'Invalid token',
                'userId': None,
                'nickname': None
            })

        req = requests.post(
             url=f"https://{settings.TitleId}.playfabapi.com/Server/GetUserAccountInfo",
             json={"PlayFabId": userId},
             headers={
                 "content-type": "application/json",
                 "X-SecretKey": settings.SecretKey
             })

        print(f"Authenticated user {userId.lower()}")
        print(f"Request to PlayFab returned status code: {req.status_code}")

        if req.status_code == 200:
             nickName = req.json().get("UserInfo",
                                       {}).get("UserAccountInfo",
                                               {}).get("Username")
             if not nickName:
                 nickName = None
             return jsonify({
                 'resultCode': 1,
                 'message':
                 f'Authenticated user {userId.lower()} title {settings.TitleId.lower()}',
                 'userId': f'{userId.upper()}',
                 'nickname': nickName
             })
        else:
             print("Failed to get user account info from PlayFab")
             successJson = {
                 'resultCode': 0,
                 'message': "Something went wrong",
                 'userId': None,
                 'nickname': None
             }
             authPostData = {}
             for key, value in authPostData.items():
                 successJson[key] = value
             print(f"Returning successJson: {successJson}")
             return jsonify(successJson)
    else:
         print(f"Invalid method: {request.method.upper()}")
         return jsonify({
             "Message":
             "Use a POST or GET Method instead of " + request.method.upper()
         })

# ------------------------------
# Existing endpoints (unchanged or minimally modified)
# ------------------------------
@app.route("/api/CachePlayFabId", methods=["POST"])
def cacheplatfabid():
    rjson = request.get_json()
    playfabCache[rjson.get("PlayFabId")] = rjson
    return jsonify({"Message": "Success"}), 200

@app.route("/api/CheckForBadName", methods=["POST"])
def check_for_bad_name():
    rjson2 = request.get_json()
    rjson = rjson2.get("FunctionResult")
    function_result = rjson2["FunctionArgument"]
    name = function_result["name"].upper()
    forRoom = function_result["forRoom"]
    playfab_id = rjson2["CallerEntityProfile"]["Lineage"]["MasterPlayerAccountId"]

    print(f"Stuff - {rjson2}")

    # For room names, always accept (no change)
    if forRoom:
        return jsonify({"result": 0})

    # Decide new display name and result code
    if name in BAD_WORDS:
        new_name = "BADGORILLA"
        result_code = 2
    else:
        new_name = name
        result_code = 0

    # Single PlayFab API call – update the display name
    requests.post(
        f"https://{settings.TitleId}.playfabapi.com/Admin/UpdateUserTitleDisplayName",
        json={"DisplayName": new_name, "PlayFabId": playfab_id},
        headers=settings.GetAuthHeaders()
    )

    return jsonify({"result": result_code})
    
@app.route("/api/GetAcceptedAgreements", methods=["POST"])
def GetAcceptedAgreements():
    return jsonify({"PrivacyPolicy": "1.1.28", "TOS": "11.05.22.2"}), 200

@app.route("/api/SubmitAcceptedAgreements", methods=["POST"])
def SubmitAcceptedAgreements():
    return jsonify({"PrivacyPolicy": "1.1.28", "TOS": "11.05.22.2"}), 200

@app.route("/api/GetName", methods=["POST"])
def GetName():
    return jsonify({"result": f"GORILLA{random.randint(1000,9999)}"})

@app.route("/api/ConsumeOculusIAP", methods=["POST"])
def consumeoculusiap():
    rjson = request.get_json()
    nonce = rjson.get("nonce")
    userId = rjson.get("userID")
    sku = rjson.get("sku")
    if not nonce or not userId or not sku:
        return jsonify({"error": True}), 400
    resp = requests.post(
        f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={userId}&sku={sku}&access_token={settings.ApiKey}",
        headers={"content-type": "application/json"}
    )
    if resp.json().get("success"):
        return jsonify({"result": True})
    return jsonify({"error": True}), 400

# ------------------------------
# CloudScript endpoints (aligned with index.js)
# ------------------------------
@app.route("/api/ReturnMyOculusHashV2", methods=["POST"])
def returnmyoculushashv2():
    return returnFunctionJson(request.get_json(), "ReturnMyOculusHash")

@app.route("/api/ReturnCurrentVersionV2", methods=["POST"])
def returncurrentversionv2():
    return returnFunctionJson(request.get_json(), "ReturnCurrentVersion")

@app.route("/api/TryDistributeCurrencyV2", methods=["POST"])
def trydistributecurrencyV2():
    # This endpoint now calls the cloud script, not the custom SR logic.
    return returnFunctionJson(request.get_json(), "TryDistributeCurrency")

@app.route("/api/BroadCastMyRoomV2", methods=["POST"])
def broadcastmyroomv2():
    data = request.get_json()
    funcparam = data.get("FunctionParameter", {})
    return returnFunctionJson(data, "BroadCastMyRoom", funcparam)

# ------------------------------
# Existing: ShouldUserAutomutePlayer
# ------------------------------
@app.route("/api/ShouldUserAutomutePlayer", methods=["POST"])
def shoulduserautomuteplayer():
    return jsonify(muteCache)

# ------------------------------
# Root
# ------------------------------
@app.route("/", methods=["GET", "POST"])
def main():
    return "If the link doesnt work this will not popup."

# ------------------------------
# Run (for local development)
# ------------------------------
if __name__ == "__main__":
    app.run("0.0.0.0", 8080)

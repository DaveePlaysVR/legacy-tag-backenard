import requests
import random
from flask import Flask, jsonify, request
# This can do any update up to prop haunt * i havent tested lastest *
# IF YOU USE THIS PUT FATE IN YOU MOTD!
# discord.gg/apkland

class GameInfo:

    def __init__(self):
        self.TitleId: str = "C9605"
        self.SecretKey: str = "7Z89HZQU4SNHB41JQXDIHKFDEB9J6BHKSDRIEBFI9IYGCHJJYN"
        self.ApiKey: str = "OC|1324018454123197|e6951e7b676cfd6646fafd973269c029"

    def get_auth_headers(self):
        return {
            "content-type": "application/json",
            "X-SecretKey": self.SecretKey
        }


settings = GameInfo()
app = Flask(__name__)
playfab_cache = {}
mute_cache = {}
PLAYFAB_API_URL = f"https://{settings.TitleId}.playfabapi.com"

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

def return_function_json(data, funcname, funcparam={}):
    user_id = data["FunctionParameter"]["CallerEntityProfile"]["Lineage"][
        "TitlePlayerAccountId"]

    response = requests.post(
        url=
        f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": user_id,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers=settings.get_auth_headers())

    if response.status_code == 200:
        return jsonify(response.json().get("data").get(
            "FunctionResult")), response.status_code
    else:
        return jsonify({}), response.status_code


def get_is_nonce_valid(nonce, oculus_id):
    response = requests.post(
        url=
        f'https://graph.oculus.com/user_nonce_validate?nonce={nonce}&user_id={oculus_id}&access_token={settings.ApiKey}',
        headers={"content-type": "application/json"})
    return response.json().get("is_valid")

# helpers ig
def playfab_request(endpoint, payload):
    url = f"{PLAYFAB_API_URL}/Server/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-SecretKey": {settings.SecretKey}
    }
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_player_data(playfab_id, keys):
    """Fetch specific keys from Player Internal Data (Server API)."""
    resp = playfab_request("GetUserInternalData", {
        "PlayFabId": playfab_id,
        "Keys": keys
    })
    data = resp.get("data", {}).get("Data", {})
    result = {}
    for key in keys:
        val = data.get(key, {}).get("Value")
        if val:
            # values are base64 encoded? Actually PlayFab returns them as Base64 strings.
            # For simplicity we assume we stored JSON strings directly.
            # If using GetUserInternalData, the Value is a base64 string; we decode.
            import base64
            decoded = base64.b64decode(val).decode('utf-8')
            try:
                result[key] = json.loads(decoded)
            except:
                result[key] = decoded
        else:
            result[key] = None
    return result

def set_player_data(playfab_id, data_dict):
    """Store multiple keys in Player Internal Data."""
    # Data must be Base64 encoded strings
    import base64
    encoded = {}
    for k, v in data_dict.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v)
        elif not isinstance(v, str):
            v = str(v)
        encoded[k] = base64.b64encode(v.encode('utf-8')).decode('ascii')
    playfab_request("UpdateUserInternalData", {
        "PlayFabId": playfab_id,
        "Data": encoded
    })

@app.route("/", methods=["POST", "GET"])
def main():
    return "hey your not suppose to be herre you dummy, stop tyna mod the game!"


@app.route("/api/CachePlayFabId", methods=["GET", "POST"])
def cacheplayfabid():

  left_pocket_dog_shit = request.get_json()

  plat = left_pocket_dog_shit.get("Platform")
  plat_userId = left_pocket_dog_shit.get("PlatformUserId")
  session_ticket = left_pocket_dog_shit.get("SessionTicket")
  playfab_id = left_pocket_dog_shit.get("PlayFabId")
  title_id = left_pocket_dog_shit.get("TitleId")

  return jsonify({
    "Message": "Yay Your Authed",
    "PlayFabId": playfab_id,
    "KidAccessToken": left_pocket_dog_shit.get("KidAccessToken"),
    "KidRefreshToken": left_pocket_dog_shit.get("KidRefreshToken"),
    "KidUrlBasePath": left_pocket_dog_shit.get("KidUrlBasePath"),
    "LocationCode": left_pocket_dog_shit.get("LocationCode")
  }), 200


@app.route("/api/PlayFabAuthentication", methods=["POST","GET"])
def skibidi():
    pluh = request.get_json()
    app_id = pluh.get('AppId')
    app_version = pluh.get('AppVersion')
    nonce = pluh.get('Nonce')
    oculus_id = pluh.get('OculusId')
    platform = pluh.get('Platform')
    age_catagory = pluh.get('AgeCategory')
    mother_token = pluh.get('MothershipToken')
    mother_shipid = pluh.get('MothershipId')

    login_req = requests.post(
        url = f'https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId',
        json = {
            'ServerCustomId': "OCULUS" + oculus_id,
            'CreateAccount': True
        },
        headers = {
            'X-SecretKey': settings.SecretKey,
            'Content-Type': 'application/json'
        })

    if login_req.status_code == 200:
        rjson = login_req.json()

        session_ticket = rjson.get('data').get('SessionTicket')
        entity_token = rjson.get('data').get('EntityToken').get('EntityToken')
        playfab_id = rjson.get('data').get('PlayFabId')
        entity_id = rjson.get('data').get('EntityToken').get('Entity').get('Id')
        entity_type = rjson.get('data').get('EntityToken').get('Entity').get('Type')
        kid_access_token = rjson.get('data').get('KidAccessToken')
        kid_refresh_token = rjson.get('data').get('KidRefreshToken')
        kid_url_base_path = rjson.get('data').get('KidUrlBasePath')
        location_code = rjson.get('data').get('LocationCode')

        link_req = requests.post(
            url = f'https://{settings.TitleId}.playfabapi.com/Client/LinkCustomID',
            json = {
                'PlayFabId': playfab_id,
                'CustomId': "OCULUS" + oculus_id,
                'ForceLink': True
            },
            headers = {
                'X-Authorization': session_ticket,
                'Content-Type': 'application/json'
            })

        return jsonify({
            "SessionTicket": session_ticket,
            "EntityToken": entity_token,
            "PlayFabId": playfab_id,
            "EntityId": entity_id,
            "EntityType": entity_type,
            "KidAccessToken": kid_access_token,
            "KidRefreshToken": kid_refresh_token,
            "KidUrlBasePath": kid_url_base_path,
            "LocationCode": location_code
        }), 200
    else: 
        ban_info = login_req.json()
        if ban_info.get("errorCode") == 1002:
            ban_message = ban_info.get("errorMessage", "No ban message provided.")
            ban_details = ban_info.get("errorDetails", {})
            ban_expiration_key = next(iter(ban_details.keys()), None)
            ban_expiration_list = ban_details.get(ban_expiration_key, [])
            ban_expiration = (
                ban_expiration_list[0]
                if len(ban_expiration_list) > 0
                else "Indefinite"
            )
            return (
                jsonify(
                    {
                        "BanMessage": ban_expiration_key,
                        "BanExpirationTime": ban_expiration,
                    }
                ),
                403
            )
@app.route("/api/TitleData", methods=["POST"])
@app.route("/v1/title-data/client", methods=["POST"])
@app.route('/api/TD', methods=['POST'])
def titled_data():
    response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/GetTitleData",
        headers=settings.get_auth_headers()
    )
    if response.status_code == 200:
        return jsonify(response.json().get("data", {}).get("Data", {}))
    else:
        return jsonify({}), response.status_code

@app.route("/api/ConsumeOculusIAP", methods=["POST"])
def consume_oculus_iap():
    rjson = request.get_json()

    access_token = rjson.get("userToken")
    user_id = rjson.get("userID")
    nonce = rjson.get("nonce")
    sku = rjson.get("sku")

    response = requests.post(
        url=
        f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={user_id}&sku={sku}&access_token={settings.ApiKey}",
        headers={"content-type": "application/json"})

    if response.json().get("success"):
        return jsonify({"result": True})
    else:
        return jsonify({"error": True})
        
@app.route("/api/ConsumeCodeItem", methods=["POST"])
def consume_code_item():
    rjson = request.get_json()
    code = rjson.get("itemGUID")
    playfab_id = rjson.get("playFabID")
    session_ticket = rjson.get("playFabSessionTicket")

    if not all([code, playfab_id, session_ticket]):
        return jsonify({"error": "Missing parameters"}), 400

    raw_url = f"" 
    response = requests.get(raw_url)

    if response.status_code != 200:
        return jsonify({"error": "GitHub fetch failed"}), 500

    lines = response.text.splitlines()
    codes = {split[0].strip(): split[1].strip() for line in lines if (split := line.split(":")) and len(split) == 2}

    if code not in codes:
        return jsonify({"result": "CodeInvalid"}), 404

    if codes[code] == "AlreadyRedeemed":
        return jsonify({"result": codes[code]}), 200

    grant_response = requests.post(
        f"https://{settings.TitleId}.playfabapi.com/Admin/GrantItemsToUsers",
        json={
            "ItemGrants": [
                {
                    "PlayFabId": playfab_id,
                    "ItemId": item_id,
                    "CatalogVersion": "DLC"
                } for item_id in ["dis da cosmetics", "anotehr cposmetic", "anotehr"]
            ]
        },
        headers=settings.get_auth_headers()
    )


    if grant_response.status_code != 200:
        return jsonify({"result": "PlayFabError", "errorMessage": grant_response.json().get("errorMessage", "Grant failed")}), 500

    new_lines = [f"{split[0].strip()}:AlreadyRedeemed" if split[0].strip() == code else line.strip() 
             for line in lines if (split := line.split(":")) and len(split) >= 2]

    updated_content = "\n".join(new_lines).strip()

    return jsonify({"result": "Success", "itemID": code, "playFabItemName": codes[code]}), 200

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
        headers=settings.get_auth_headers()
    )

    return jsonify({"result": result_code})

@app.route("/api/GetAcceptedAgreements", methods=["POST", "GET"])
def get_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)

@app.route("/api/SubmitAcceptedAgreements", methods=["POST", "GET"])
def submit_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)

@app.route("/api/ReturnMyOculusHashV2")
def return_my_oculus_hash_v2():
    return return_function_json(request.get_json(), "ReturnMyOculusHash")

@app.route('/api/GetTier', methods=['POST'])
def get_tier():
    try:
        body = request.get_json() or {}
        playfabids = body.get('playfabIds', [])
        if not playfabids:
            return jsonify([]), 200

        results = []
        for pid in playfabids:
            # Get or initialize ranked data for this player
            data = get_player_data(pid, ["RankedData"])
            ranked = data.get("RankedData")
            if not ranked:
                ranked = {
                    "PC": {"elo": 1000.0, "majorTier": 0, "minorTier": 0, "rankProgress": 0.0},
                    "Quest": {"elo": 1000.0, "majorTier": 0, "minorTier": 0, "rankProgress": 0.0}
                }
            platformdata = []
            for plat in ["PC", "Quest"]:
                entry = ranked.get(plat, {})
                platformdata.append({
                    "platform": plat,
                    "elo": entry.get("elo", 1000.0),
                    "majorTier": entry.get("majorTier", 0),
                    "minorTier": entry.get("minorTier", 0),
                    "rankProgress": entry.get("rankProgress", 0.0),
                })
            results.append({
                "playfabID": pid,
                "platformData": platformdata,
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/CreateMatchId', methods=['POST'])
def create_match_id():
    try:
        body = request.get_json() or {}
        mothershipid = body.get('mothershipId')
        platform = body.get('platform', "PC")
        matchid = str(uuid.uuid4())

        matches = get_title_data(["ActiveMatches"]).get("ActiveMatches") or []
        now = datetime.utcnow()
        
        active = [m for m in matches if (now - datetime.fromisoformat(m['created'])) < timedelta(hours=1)]
        active.append({
            "matchid": matchid,
            "createdby": mothershipid,
            "platform": platform,
            "isactive": True,
            "created": now.isoformat(),
            "lastping": now.isoformat()
        })
        set_title_data({"ActiveMatches": active})
        return matchid, 200
    except Exception as e:
        return "", 500

@app.route('/api/ValidateMatchJoin', methods=['POST'])
def validate_match_join():
    try:
        body = request.get_json() or {}
        matchid = body.get('matchId')
        mothershipid = body.get('mothershipId')
        if not matchid:
            return jsonify({"validJoin": False}), 200

        matches = get_title_data(["ActiveMatches"]).get("ActiveMatches") or []
        match = next((m for m in matches if m['matchid'] == matchid and m.get('isactive', True)), None)
        if match:
            return jsonify({"validJoin": True}), 200
        return jsonify({"validJoin": False}), 200
    except Exception as e:
        return jsonify({"validJoin": False}), 500

@app.route('/api/SubmitMatchScores', methods=['POST'])
def submit_match_scores():
    try:
        body = request.get_json() or {}
        matchid = body.get('matchId')
        scores = body.get('playerScores', [])
        if not matchid or not scores or len(scores) < 2:
            return "OK", 200

        sorted_scores = sorted(scores, key=lambda x: x.get('gameScore', 0), reverse=True)
        playercount = len(scores)

        for i, sc in enumerate(sorted_scores):
            pid = sc.get('playfabId')
            if not pid:
                continue
            data = get_player_data(pid, ["RankedData"])
            ranked = data.get("RankedData") or {}
            # Determine platform (assume PC)
            plat = "PC"
            entry = ranked.get(plat, {})
            elo = entry.get("elo", 1000.0)
            placement = i / (playercount - 1)
            elochange = (1 - placement) * 20 - 10
            elo = max(0, elo + elochange)

            # Recalculate tier
            if elo >= 2000:
                major, minor, progress = 5, 0, 1.0
            elif elo >= 1600:
                major = 4
                minor = int((elo - 1600) / 133)
                progress = ((elo - 1600) % 133) / 133
            elif elo >= 1200:
                major = 3
                minor = int((elo - 1200) / 133)
                progress = ((elo - 1200) % 133) / 133
            elif elo >= 800:
                major = 2
                minor = int((elo - 800) / 133)
                progress = ((elo - 800) % 133) / 133
            elif elo >= 400:
                major = 1
                minor = int((elo - 400) / 133)
                progress = ((elo - 400) % 133) / 133
            else:
                major = 0
                minor = int(elo / 133)
                progress = (elo % 133) / 133

            entry["elo"] = elo
            entry["majorTier"] = major
            entry["minorTier"] = min(minor, 2)
            entry["rankProgress"] = progress
            ranked[plat] = entry
            set_player_data(pid, {"RankedData": ranked})

        matches = get_title_data(["ActiveMatches"]).get("ActiveMatches") or []
        for m in matches:
            if m['matchid'] == matchid:
                m['isactive'] = False
        set_title_data({"ActiveMatches": matches})
        return "OK", 200
    except Exception as e:
        return "Error", 500

@app.route('/api/PingRoom', methods=['POST'])
def ping_room():
    try:
        body = request.get_json() or {}
        matchid = body.get('matchId')
        if matchid:
            matches = get_title_data(["ActiveMatches"]).get("ActiveMatches") or []
            for m in matches:
                if m['matchid'] == matchid:
                    m['lastping'] = datetime.utcnow().isoformat()
            set_title_data({"ActiveMatches": matches})
        return "OK", 200
    except Exception as e:
        return "Error", 500

@app.route('/api/UnlockCompetitiveQueue', methods=['POST'])
def unlock_competitive_queue():
    try:
        body = request.get_json() or {}
        mothershipid = body.get('mothershipId')
        platform = body.get('platform', "PC")
        unlocked = body.get('unlocked', False)
        if mothershipid:
            # Store in Player Data
            data = get_player_data(mothershipid, ["CompetitiveUnlock"])
            unlocks = data.get("CompetitiveUnlock") or {}
            unlocks[platform] = unlocked
            set_player_data(mothershipid, {"CompetitiveUnlock": unlocks})
        return "OK", 200
    except Exception as e:
        return "Error", 500

@app.route('/api/CCU', methods=["POST"])
def ccu():
    rjson = request.get_json(force=True, silent=True)  # Ignores Content-Type header
    print(f"Received: {rjson}")
    if rjson is None:
        print("rjson is null.")
    # Return a dummy concurrent user count
    return jsonify({"count": random.randint(100, 500), "errorMessage": None}), 200

@app.route("/api/ReturnCurrentVersionV2", methods=["POST", "GET"])
def return_current_version_v2():
    return return_function_json(request.get_json(), "ReturnCurrentVersion")

@app.route("/api/TryDistributeCurrencyV2", methods=["POST", "GET"])
def try_distribute_currency_v2():
    return return_function_json(request.get_json(), "TryDistributeCurrency")

@app.route("/api/BroadCastMyRoomV2", methods=["POST", "GET"])
def broadcast_my_room_v2():
    return return_function_json(request.get_json(), "BroadCastMyRoom",
                                request.get_json()["FunctionParameter"])

@app.route("/api/ShouldUserAutomutePlayer", methods=["POST", "GET"])
def should_user_automute_player():
    return jsonify(mute_cache)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1416)


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
                "X-SecretKey": settings.SecretKey
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

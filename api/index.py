import requests
import random
from flask import Flask, jsonify, request
from datetime import datetime, timedelta

class GameInfo():
    def __init__(self):
        self.TitleId : str = "FE314"
        self.SecretKey : str = "WUSAOXAYS9TKAANYF3N77JFEJYD6N571JHEUN83NKHWBH3DFD4"
        self.ApiKey : str = "OC|1243808488818929|a88a73bc8d73237018c75eee39f5bb48"

    def GetAuthHeaders(self) -> dict:
        return {
            "content-type": "application/json",
            "X-SecretKey": self.SecretKey
        }

    def GetTitle(self) -> str:
        return self.TitleId


settings : GameInfo = GameInfo()
app : Flask = Flask(__name__)
playfabCache : dict = {}
muteCache : dict = {}

def ReturnFunctionJson(data, funcname, funcparam = {}):
    rjson = data["FunctionParameter"]

    userId : str = rjson.get("CallerEntityProfile").get("Lineage").get("TitlePlayerAccountId")

    req = requests.post(
        url = f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json = {
            "PlayFabId": userId,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers = settings.GetAuthHeaders()
    )

    if req.status_code == 200:
        return jsonify(req.json().get("data").get("FunctionResult")), req.status_code
    else:
        return jsonify({}), req.status_code

def GetIsNonceValid(nonce : str, oculusId : str):
    req = requests.post(
        url = f'https://graph.oculus.com/user_nonce_validate?nonce=' + nonce + '&user_id=' + oculusId  + '&access_token=' + settings.ApiKey,
        headers = {
            "content-type": "application/json"
        }
    )
    return req.json().get("is_valid")

@app.route("/", methods = ["POST", "GET"])
def main():
    return "If the link doesnt work this will not popup."

def AttestationAuthentication(AttestationToken):
    url = (
        "https://graph.oculus.com/platform_integrity/verify"
        f"?token={AttestationToken}&access_token={settings.ApiKey}"
    )
    resp = requests.get(url)
    return resp.json()

def VerifyOculusStandards(userId, nonce):
    validate_url = "https://graph.oculus.com/user_nonce_validate"
    validate_payload = {
        "access_token": settings.ApiKey,
        "nonce": nonce,
        "user_id": userId
    }

    try:
        response = requests.post(validate_url, data=validate_payload)
        response.raise_for_status()
        validation_data = response.json()
    except Exception as e:
        return {"is_valid": False, "org_scoped_id": None, "error": str(e)}

    if not validation_data.get("is_valid"):
        return {"is_valid": False, "org_scoped_id": None}

    org_id_url = f"https://graph.oculus.com/{userId}"
    org_id_params = {
        "access_token": settings.ApiKey,
        "fields": "org_scoped_id"
    }

    try:
        org_response = requests.get(org_id_url, params=org_id_params)
        org_response.raise_for_status()
        org_data = org_response.json()
        org_scoped_id = org_data.get("org_scoped_id")
    except Exception as e:
        return {"is_valid": True, "org_scoped_id": None, "error": str(e)}

    return {"is_valid": True, "org_scoped_id": org_scoped_id}


@app.route("/api/authenticate/attestation/getNonce", methods=["POST"])
def GetNonce():
    data = request.get_json()

    user_id = data.get("UserId")
    nonce = data.get("Nonce")

    if not user_id:
        return jsonify({"error": "The user id provided is null, empty or undefined"}), 400

    if not nonce:
        return jsonify({"error": "The nonce provided is null, empty or undefined"}), 400

    verification = VerifyOculusStandards(user_id, nonce)

    if not verification["is_valid"]:
        return jsonify({
            "error": "The user information details provided are invalid and or undefined"
    }), 403

    challengeNonce = secrets.token_urlsafe(16)
    currentNonces[user_id] = challengeNonce

    return jsonify({
        "challenge_nonce": challengeNonce,
        "org_scoped_id": verification["org_scoped_id"]
    })

@app.route("/api/authenticate/attestation/mothershipAuth", methods=["POST"])
def MotherShipAuth():
    rjson = request.get_json()
    user_id = rjson.get("UserId")
    attestation_token = rjson.get("AttestationToken")

    if not attestation_token or attestation_token.strip() == "":
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership authentication attestation token is null or empty.",
            "BanExpirationTime": "Unkown"
        }), 403

    data = AttestationAuthentication(attestation_token)

    if "data" not in data or len(data["data"]) == 0:
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership authentication responded with a value less then 1, the attestation authentication must return a value greater then 0 and not less then 0, example: 1, 2, 3, 4. But the response is less then 1. eg: the Validation responded with null or empty data.",
            "BanExpirationTime": "Unkown"
        }), 403

    response_data = data["data"][0]

    if response_data.get("message") == "invalid signature":
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with a invalid attestation token authentication signature, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to you token having an invalid signature.",
            "BanExpirationTime": "Unkown"
        }), 403

    if response_data.get("message") == "token expired":
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with your attestation token authentication being expired, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to your token being expired.",
            "BanExpirationTime": "Unkown"
        }), 403

    if response_data.get("message") != "success":
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with your attestation token authentication being a invalid token, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to your token being invalid and not a valid attestation authentication request.",
            "BanExpirationTime": "Unkown"
        }), 403

    claims = response_data.get("claims")
    decoded_bytes = base64.urlsafe_b64decode(claims + "==")
    claims_json = json.loads(decoded_bytes)

    request_details = claims_json.get("request_details", {})
    app_state = claims_json.get("app_state", {})
    device_state = claims_json.get("device_state", {})
    device_ban = claims_json.get("device_ban", {})
    security_state = claims_json.get("device_state", {})

    unique_id = device_state.get("unique_id") if device_state else None
    device_integrity_state = device_state.get("device_integrity_state") if device_state else None
    StoreRecognized = app_state.get("app_integrity_state") if app_state else None
    securityUpdate = security_state.get("security_update_pending_days") if security_state else None
    packageId = app_state.get("package_id") if app_state else None
    Sha256Sig = app_state.get("package_cert_sha256_digest") if app_state else None
    device_ban_status = device_ban.get("is_banned") if device_ban else False

    if Sha256Sig is None or Cert not in Sha256Sig:
        return jsonify({
            "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication has rejected your request due to your package cert being unrecognized.",
            "BanExpirationTime": "Unknown"
        }), 403

    if device_ban_status:
        return jsonify({
            "BanMessage": "Your device is currently banned from this application.",
            "BanExpirationTime": device_ban.get("remaining_ban_time", "Unknown")
        }), 403

    if unique_id is None or device_integrity_state is None or StoreRecognized is None or packageId is None or Sha256Sig is None:
            return jsonify({
                "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with no data. the data must be greater then 0, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to the authentication response return is null or empty or less then 1.",
                "BanExpirationTime": "Unkown"
            }), 403

    if packageId != Valid_Package:
            return jsonify({
                "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with your package id being a unkown package cert, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to the authentication response returning a unkown package cert.",
                "BanExpirationTime": "Unkown"
            }), 403

    if device_integrity_state != "Advanced":
            return jsonify({
                "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with your device integrity state being untrusted, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to the authentication response returning your device integrity state being untrusted.",
                "BanExpirationTime": "Unkown"
            }), 403

    if StoreRecognized != "StoreRecognized":
            return jsonify({
                "BanMessage": "OCULUS INTEGRITY AUTHENTICATION FAILED. REASON: The mothership attestation authentication responded with your download source being a invalid download director source, please check you are on the latest version of the game. The attestation authentication has refused your authentication request due to the authentication response returning your download source being unrecongnised.",
                "BanExpirationTime": "Unkown"
            }), 403

    return jsonify({
            "Success!": "OCULUS INTEGRITY AUTHENTICATION PASSED. REASON: The mothership attestation authentication responded with your authentication validation being valid"
            })

@app.route("/api/PlayFabAuthentication", methods = ["POST", "GET"])
def playfabauthentication():
    rjson = request.get_json()

    if rjson.get("CustomId") is None:
        return jsonify({"Message":"Missing CustomId parameter","Error":"BadRequest-NoCustomId"})
    if rjson.get("Nonce") is None:
        return jsonify({"Message":"Missing Nonce parameter","Error":"BadRequest-NoNonce"})
    if rjson.get("AppId") is None:
        return jsonify({"Message":"Missing AppId parameter","Error":"BadRequest-NoAppId"})
    if rjson.get("Platform") is None:
        return jsonify({"Message":"Missing Platform parameter","Error":"BadRequest-NoPlatform"})
    if rjson.get("OculusId") is None:
        return jsonify({"Message":"Missing OculusId parameter","Error":"BadRequest-NoOculusId"})

    if rjson.get("AppId") != settings.TitleId:
        return jsonify({"Message":"Request sent for the wrong App ID","Error":"BadRequest-AppIdMismatch"})
    if not rjson.get("CustomId").startswith("OC") and not rjson.get("CustomId").startswith("PI"):
        return jsonify({"Message":"Bad request","Error":"BadRequest-No OC or PI Prefix"})

    url = f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId"
    login_request = requests.post(
        url = url,
        json = {
            "ServerCustomId": rjson.get("CustomId"),
            "CreateAccount": True
        },
        headers = settings.GetAuthHeaders()
    )
    
    if login_request.status_code == 200:
        data =  login_request.json().get("data")
        sessionTicket = data.get("SessionTicket")
        entityToken = data.get("EntityToken").get("EntityToken")
        playFabId = data.get("PlayFabId")
        entityType = data.get("EntityToken").get("Entity").get("Type")
        entityId = data.get("EntityToken").get("Entity").get("Id")

        print(requests.post(
            url = f"https://{settings.TitleId}.playfabapi.com/Client/LinkCustomID",
            json = {
                "ForceLink": True,
                "CustomId": rjson.get("CustomId")
            },
            headers = settings.GetAuthHeaders()
        ).json())

        return jsonify({
            "PlayFabId": playFabId,
            "SessionTicket": sessionTicket,
            "EntityToken": entityToken,
            "EntityId": entityId,
            "EntityType": entityType
        })
    else:
        if login_request.status_code == 403:
            ban_info = login_request.json()
            if ban_info.get('errorCode') == 1002:
                ban_message = ban_info.get('errorMessage', "No ban message provided.")
                ban_details = ban_info.get('errorDetails', {})
                ban_expiration_key = next(iter(ban_details.keys()), None)
                ban_expiration_list = ban_details.get(ban_expiration_key, [])
                ban_expiration = ban_expiration_list[0] if len(ban_expiration_list) > 0 else "No expiration date provided."
                print(ban_info)
                return jsonify({
                    'BanMessage': ban_expiration_key,
                    'BanExpirationTime': ban_expiration
                }), 403
            else:
                error_message = ban_info.get('errorMessage', 'Forbidden without ban information.')
                return jsonify({
                    'Error': 'PlayFab Error',
                    'Message': error_message
                }), 403
        else:
            error_info = login_request.json()
            error_message = error_info.get('errorMessage', 'An error occurred.')
            return jsonify({
                'Error': 'PlayFab Error',
                'Message': error_message
            }), login_request.status_code
            
@app.route("/api/CachePlayFabId", methods = ["POST","GET"])
def cacheplatfabid():
    rjson = request.get_json()

    playfabCache[rjson.get("PlayFabId")] = rjson

    return jsonify({"Message":"Success"}), 200

@app.route('/api/TitleData', methods=['POST'])
def titled_data():
    return jsonify({"MOTD": "<color=#ff8d0a>   [ > WELCOME TO PROJECT LUNAR! < ]  </color>\n<color=#ff00ee>   BOOST https://discord.gg/gaj8PHafq3 FOR EVERY COSMETIC!</color>\n<color=#783be3>   CREDITS: Z4EU, LUNRRR</color>\n<color=#2ef1ff>   THIS GAME TAKES YOU INTO OLDER AND NEWER GTAG UPDATES!</color><color=#bb1b1b>\n   YOU DON'T NEED TO CHANGE YOU'RE NAME!!</color>"})

    if req.status_code == 200:
        return jsonify(req.json().get("data").get("Data"))
    else:
        return jsonify({})

@app.route("/api/CheckForBadName", methods=["POST", "GET"])
def checkforbadname():
    rjson = request.get_json() 
    function_result = rjson["FunctionArgument"]
    playfab_id = rjson["CallerEntityProfile"]["Lineage"]["MasterPlayerAccountId"]
    name = function_result["name"].upper()
    forRoom = function_result["forRoom"]

    if forRoom == True:
        return jsonify({"result": 0})

    link_response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Admin/UpdateUserTitleDisplayName",
        json={
            "DisplayName": name,
            "PlayFabId": playfab_id,
        },
        headers=settings.GetAuthHeaders(),
    ).json()
    return jsonify({"result": 0})

@app.route("/api/GetAcceptedAgreements", methods=['POST', 'GET'])
def GetAcceptedAgreements():
    data = request.json

    return jsonify({"PrivacyPolicy": "1.1.28", "TOS": "11.05.22.2"}), 200

@app.route("/api/SubmitAcceptedAgreements", methods=['POST', 'GET'])
def SubmitAcceptedAgreements():
    data = request.json

    return jsonify({"PrivacyPolicy": "1.1.28", "TOS": "11.05.22.2"}), 200

@app.route('/api/GetName', methods=['POST', 'GET'])
def GetName():
    return jsonify({"result": f"GORILLA{random.randint(1000,9999)}"})

# replace https://iap.gtag-cf.com/api/ConsumeOculusIAP with this endpoint
@app.route("/api/ConsumeOculusIAP", methods = ["POST", "GET"])
def consumeoculusiap():
    rjson = request.get_json()

    accessToken = rjson.get("userToken")
    userId = rjson.get("userID")
    playFabId = rjson.get("playFabId")
    nonce = rjson.get("nonce")
    platform = rjson.get("platform")
    sku = rjson.get("sku")
    debugParams = rjson.get("debugParemeters")

    req = requests.post(
        url = f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={userId}&sku={sku}&access_token={settings.ApiKey}",
        headers = {
            "content-type": "application/json"
        }
    )

    if bool(req.json().get("success")):
        return jsonify({"result":True})
    else:
        return jsonify({"error":True})

@app.route("/api/ReturnMyOculusHashV2")
def returnmyoculushashv2():
    return ReturnFunctionJson(request.get_json(), "ReturnMyOculusHash")

@app.route("/api/ReturnCurrentVersionV2", methods = ["POST", "GET"])
def returncurrentversionv2():
    return ReturnFunctionJson(request.get_json(), "ReturnCurrentVersion")

@app.route("/api/TryDistributeCurrencyV2", methods=["POST"])
def TryDistributeCurrencyV2():
    if request.method != "POST":
        return "", 404
        
    rjson = request.json
    sr_a_day = 100
    current_player_id = rjson.get("CallerEntityProfile", {}).get("Lineage", {}).get("MasterPlayerAccountId")

    get_data_response = requests.post(
        f"https://{settings.TitleId}.playfabapi.com/Server/GetUserReadOnlyData",
        headers=settings.get_auth_headers(),
        json={
            "PlayFabId": current_player_id,
            "Keys": ["DailyLogin"]
        }
    )

    daily_login_value = get_data_response.json().get("data").get("Data").get("DailyLogin", {}).get("Value", None)

    last_login_date = None
    if daily_login_value:
        last_login_date = datetime.fromisoformat(daily_login_value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if not last_login_date or last_login_date < datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc):
        requests.post(
            f"https://{settings.TitleId}.playfabapi.com/Server/AddUserVirtualCurrency",
            headers=settings.get_auth_headers(),
            json={
                "PlayFabId": current_player_id,
                "VirtualCurrency": "SR",
                "Amount": sr_a_day
            }
        )

        requests.post(
            f"https://{settings.TitleId}.playfabapi.com/Server/UpdateUserReadOnlyData",
            headers=settings.get_auth_headers(),
            json={
                "PlayFabId": current_player_id,
                "Data": {
                    "DailyLogin": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).isoformat()
                }
            }
        )

    return "", 200

@app.route("/api/BroadCastMyRoomV2", methods = ["POST", "GET"])
def broadcastmyroomv2():
    return ReturnFunctionJson(request.get_json(), "BroadCastMyRoom", request.get_json()["FunctionParameter"])

@app.route("/api/ShouldUserAutomutePlayer", methods = ["POST", "GET"])
def shoulduserautomuteplayer():
    return jsonify(muteCache)

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


def ReturnFunctionJson(data, funcname, funcparam={}):
    print(f"Calling function: {funcname} with parameters: {funcparam}")
    rjson = data.get("FunctionParameter", {})
    userId = rjson.get("CallerEntityProfile",
                       {}).get("Lineage", {}).get("TitlePlayerAccountId")

    print(f"UserId: {userId}")

    req = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": userId,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers={
            "content-type": "application/json",
            "X-SecretKey": secretkey
        })

    if req.status_code == 200:
        result = req.json().get("data", {}).get("FunctionResult", {})
        print(f"Function result: {result}")
        return jsonify(result), req.status_code
    else:
        print(f"Function execution failed, status code: {req.status_code}")
        return jsonify({}), req.status_code

if __name__ == "__main__":

    app.run("0.0.0.0", 8080)

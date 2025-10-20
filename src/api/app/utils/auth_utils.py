import base64
import json
import logging

logger = logging.getLogger(__name__)

def get_sample_user():
    return {
        "user_principal_id": "guest-user-00000000",
        "user_name": "Guest User",
        "auth_provider": None,
        "auth_token": None,
        "aad_id_token": None,
        "client_principal_b64": None,
        "is_guest": True
    }

def get_authenticated_user_details(request_headers):
    user_object = {}

    normalized_headers = {k.lower(): v for k, v in request_headers.items()}
    
    # Enhanced debugging: Log all headers to see what we're getting
    logger.info(f"🔍 AUTH_UTILS: All request headers received: {list(request_headers.keys())}")
    logger.info(f"🔍 AUTH_UTILS: Looking for Easy Auth headers: {[k for k in normalized_headers.keys() if 'x-ms-client' in k]}")
    
    # Log the actual Easy Auth header values if they exist
    easy_auth_headers = {k: v for k, v in request_headers.items() if 'x-ms-client' in k.lower()}
    if easy_auth_headers:
        logger.info(f"🔍 AUTH_UTILS: Easy Auth headers found with values:")
        for key, value in easy_auth_headers.items():
            logger.info(f"  {key}: {value}")
    else:
        logger.info(f"🔍 AUTH_UTILS: NO Easy Auth headers found!")

    # Check for Easy Auth headers (either direct or forwarded)
    if "x-ms-client-principal-id" not in normalized_headers:
        logger.info("No Easy Auth headers found, using sample guest user")
        raw_user_object = get_sample_user()
        user_object["is_guest"] = True
    else:
        logger.info("Easy Auth headers found, extracting user details")
        raw_user_object = {k: v for k, v in request_headers.items()}
        user_object["is_guest"] = False
        logger.info(f"Easy Auth user ID: {raw_user_object.get('x-ms-client-principal-id')}")
        logger.info(f"Easy Auth user name: {raw_user_object.get('x-ms-client-principal-name')}")

    user_object["user_principal_id"] = raw_user_object.get("x-ms-client-principal-id")
    user_object["user_name"] = raw_user_object.get("x-ms-client-principal-name")
    user_object["auth_provider"] = raw_user_object.get("x-ms-client-principal-idp")
    user_object["auth_token"] = raw_user_object.get("x-ms-token-aad-id-token")
    user_object["client_principal_b64"] = raw_user_object.get("x-ms-client-principal")
    user_object["aad_id_token"] = raw_user_object.get("x-ms-token-aad-id-token")

    return user_object

def get_tenantid(client_principal_b64):
    tenant_id = ""
    if client_principal_b64:
        try:
            decoded_bytes = base64.b64decode(client_principal_b64)
            decoded_string = decoded_bytes.decode("utf-8")
            user_info = json.loads(decoded_string)
            tenant_id = user_info.get("tid")
        except Exception as ex:
            logger.exception(f"Error decoding tenant ID: {ex}")
    return tenant_id



# app/core/telegram.py
import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

def verify_telegram_webapp_init_data(
    init_data: str, 
    bot_token: str, 
    max_age_seconds: int = 300
) -> dict:
    """
    Verifies Telegram WebApp initData HMAC-SHA256 signature and freshness.
    
    Returns parsed dictionary containing user data and params if valid.
    Raises ValueError on any validation or freshness failure.
    """
    if not init_data:
        raise ValueError("initData string is empty")

    parsed_params = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed_params.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash parameter in initData")

    auth_date_str = parsed_params.get("auth_date")
    if not auth_date_str:
        raise ValueError("Missing auth_date parameter in initData")

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise ValueError("Invalid auth_date format in initData")

    now = int(time.time())
    if abs(now - auth_date) > max_age_seconds:
        raise ValueError("initData has expired or is invalid")

    # Construct data_check_string: sort key=value by key separated by \n
    data_check_lines = [f"{k}={v}" for k, v in sorted(parsed_params.items())]
    data_check_string = "\n".join(data_check_lines)

    # HMAC secret key is HMAC-SHA256 of bot_token with key "WebAppData"
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash.lower(), received_hash.lower()):
        raise ValueError("Invalid Telegram initData signature")

    user_data = {}
    if "user" in parsed_params:
        try:
            user_data = json.loads(parsed_params["user"])
        except json.JSONDecodeError:
            pass

    return {
        "user": user_data,
        "auth_date": auth_date,
        "raw": parsed_params
    }

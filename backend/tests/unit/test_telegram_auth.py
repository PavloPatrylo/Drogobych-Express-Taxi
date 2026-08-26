import hmac
import hashlib
import time
import json
from urllib.parse import urlencode
import pytest

from app.core.telegram import verify_telegram_webapp_init_data
from app.core.config import settings


def generate_valid_init_data(bot_token: str, user_dict: dict, auth_date: int = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())
        
    data = {
        "auth_date": str(auth_date),
        "query_id": "AAH...",
        "user": json.dumps(user_dict, separators=(',', ':'))
    }
    
    # Sort keys
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode('utf-8'), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    data["hash"] = hash_value
    return urlencode(data)


def test_verify_telegram_webapp_init_data_success():
    user_info = {"id": 123456789, "first_name": "John", "last_name": "Doe"}
    bot_token = settings.BOT_TOKEN
    init_data = generate_valid_init_data(bot_token, user_info)
    
    parsed = verify_telegram_webapp_init_data(init_data, bot_token)
    assert parsed["user"]["id"] == 123456789
    assert parsed["user"]["first_name"] == "John"


def test_verify_telegram_webapp_init_data_invalid_hash():
    user_info = {"id": 123456789, "first_name": "John"}
    bot_token = settings.BOT_TOKEN
    init_data = generate_valid_init_data(bot_token, user_info)
    
    # Tamper init_data
    tampered = init_data.replace("John", "Hacker")
    
    with pytest.raises(ValueError) as exc_info:
        verify_telegram_webapp_init_data(tampered, bot_token)
    assert "signature" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


def test_verify_telegram_webapp_init_data_expired():
    user_info = {"id": 123456789, "first_name": "John"}
    bot_token = settings.BOT_TOKEN
    old_date = int(time.time()) - 600 # 10 mins ago (limit is 300s)
    init_data = generate_valid_init_data(bot_token, user_info, auth_date=old_date)
    
    with pytest.raises(ValueError) as exc_info:
        verify_telegram_webapp_init_data(init_data, bot_token)
    assert "expired" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


def test_verify_telegram_webapp_init_data_future_date():
    user_info = {"id": 123456789, "first_name": "John"}
    bot_token = settings.BOT_TOKEN
    future_date = int(time.time()) + 600 # 600s in future
    init_data = generate_valid_init_data(bot_token, user_info, auth_date=future_date)
    
    with pytest.raises(ValueError) as exc_info:
        verify_telegram_webapp_init_data(init_data, bot_token)
    assert "expired" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional, Tuple


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding_len = (-len(data)) % 4
    return base64.urlsafe_b64decode((data + ("=" * padding_len)).encode("utf-8"))


def _json_loads_bytes(raw: bytes) -> Dict[str, Any]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("JWT JSON must be an object")
    return obj


def decode_jwt(token: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header_b64, payload_b64, signature_b64 = parts
    header = _json_loads_bytes(_b64url_decode(header_b64))
    payload = _json_loads_bytes(_b64url_decode(payload_b64))
    return header, payload, signature_b64


def generate_jwt_hs256(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _status_by_time(payload: Dict[str, Any], at_ts: int) -> Dict[str, Any]:
    exp = payload.get("exp")
    nbf = payload.get("nbf")

    status: Dict[str, Any] = {
        "at_ts": at_ts,
        "expired": False,
        "not_before": False,
    }

    if isinstance(exp, (int, float)):
        status["expired"] = at_ts >= int(exp)
    if isinstance(nbf, (int, float)):
        status["not_before"] = at_ts < int(nbf)

    return status


def main() -> None:
    token = input("请输入JWT令牌(留空则生成)：").strip()
    days_str = input("请输入时间(天数)：").strip()
    days = int(float(days_str)) if days_str else 0

    if not token:
        secret = "CSCaseFlow"
        now = int(time.time())
        payload: Dict[str, Any] = {
            "iss": "CSCaseFlow",
            "sub": "activation",
            "iat": now,
            "nbf": now,
            "exp": now + days * 24 * 60 * 60,
            # "exp": now + 60,
        }
        token = generate_jwt_hs256(payload, secret)
        print("生成JWT：")
        print(token)

    header, payload, _sig_b64 = decode_jwt(token)
    print("Header：")
    print(json.dumps(header, ensure_ascii=False, indent=2, sort_keys=True))
    print("Payload：")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

    now_ts = int(time.time())
    check_ts = now_ts + days * 24 * 60 * 60
    # check_ts = now_ts + 60
    status = _status_by_time(payload, check_ts)
    print("校验时间点：")
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

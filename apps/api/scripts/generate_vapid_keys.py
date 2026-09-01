"""Railway 웹 푸시 환경변수에 넣을 VAPID 키 한 쌍을 출력한다."""

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02, b64urlencode


def main() -> None:
    vapid = Vapid02()
    vapid.generate_keys()
    private_key = vapid.private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_key = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    print(f"WEB_PUSH_VAPID_PUBLIC_KEY={b64urlencode(public_key)}")
    print(f"WEB_PUSH_VAPID_PRIVATE_KEY={b64urlencode(private_key)}")


if __name__ == "__main__":
    main()

"""저장소 주소 → 키 변환.

카드 생성은 원본을 **버킷에서 직접 읽는다**(`integrations/storage.py` 설명). 그래서
"이 주소가 우리 것인가"를 가리는 이 함수가 뚫리면 남의 주소를 읽으러 가거나 버킷
안의 엉뚱한 객체를 읽는다. DB 도 네트워크도 필요 없는 순수 함수라 여기서 직접 센다.
"""

import pytest

from app.core.config import settings
from app.integrations import storage

BASE = "https://cdn.example.test"


@pytest.fixture(autouse=True)
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """conftest 가 S3 설정을 비워 두므로(`_neutralize_image_origin`) 여기서 채운다."""
    monkeypatch.setattr(settings, "s3_bucket_name", "omeong-bucket")
    monkeypatch.setattr(settings, "s3_public_base_url", BASE)


def test_우리_주소면_키만_남는다() -> None:
    key = storage.object_key_from_public_url(f"{BASE}/travel-log/2026/09/abc.jpg")

    assert key == "travel-log/2026/09/abc.jpg"


def test_호스트를_앞에_붙인_주소는_통과하지_못한다() -> None:
    """`startswith` 로 비교하면 통과한다 — 실제 접속 대상은 evil.test 다.

    `schemas/validators.py` 가 같은 함정을 막는 이유와 같다.
    """
    assert storage.object_key_from_public_url("https://cdn.example.test@evil.test/x.jpg") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/travel-log/x.jpg",
        "https://cdn.example.test.evil.test/x.jpg",
        f"{BASE}/",
        f"{BASE}/../../etc/passwd",
        "travel-log/2026/09/abc.jpg",
    ],
)
def test_우리_것이_아니거나_모양이_아니면_None(url: str) -> None:
    assert storage.object_key_from_public_url(url) is None


def test_대소문자가_달라도_같은_호스트로_본다() -> None:
    """호스트에서 대소문자는 뜻이 없다."""
    assert storage.object_key_from_public_url("https://CDN.Example.Test/a/b.jpg") == "a/b.jpg"


def test_설정이_없으면_None(monkeypatch: pytest.MonkeyPatch) -> None:
    """S3 가 안 붙은 환경에서 키를 만들어 내면 없는 버킷을 읽으러 간다."""
    monkeypatch.setattr(settings, "s3_public_base_url", "")

    assert storage.object_key_from_public_url(f"{BASE}/a/b.jpg") is None


def test_공개_주소에_경로가_붙어_있어도_그만큼만_떼어낸다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CloudFront 를 하위 경로에 붙이는 구성도 있다."""
    monkeypatch.setattr(settings, "s3_public_base_url", f"{BASE}/media/")

    assert (
        storage.object_key_from_public_url(f"{BASE}/media/travel-log/a.jpg") == "travel-log/a.jpg"
    )
    # 접두사 밖의 주소는 우리 것이 아니다.
    assert storage.object_key_from_public_url(f"{BASE}/other/a.jpg") is None


def test_키를_만들_때_접두사와_확장자가_지켜진다() -> None:
    key = storage.build_object_key("travel-log-card", "png")

    assert key.startswith("travel-log-card/")
    assert key.endswith(".png")

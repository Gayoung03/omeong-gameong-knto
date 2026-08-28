"""이미지 URL 출처 검증자 단위 테스트.

DB 없이 순수 함수만 본다. autouse 로 S3 설정을 비우는 conftest 픽스처가 걸려
있으므로, 각 테스트는 필요한 설정을 자기 손으로 다시 세팅한다(나중 monkeypatch 가
이긴다).
"""

import pytest

from app.core.config import settings
from app.schemas.validators import validate_image_url


def _set_host(
    monkeypatch: pytest.MonkeyPatch, base_url: str, environment: str = "production"
) -> None:
    monkeypatch.setattr(settings, "s3_public_base_url", base_url)
    monkeypatch.setattr(settings, "environment", environment)


def test_none은_그대로_통과한다(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "https://cdn.example.com")
    assert validate_image_url(None) is None


def test_허용_호스트와_정확히_일치하면_통과(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "https://cdn.example.com")
    url = "https://cdn.example.com/pets/a.jpg"
    assert validate_image_url(url) == url


def test_호스트_대소문자는_무시한다(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "https://cdn.example.com")
    url = "https://CDN.Example.COM/pets/a.jpg"
    assert validate_image_url(url) == url


def test_다른_호스트는_거부한다(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "https://cdn.example.com")
    with pytest.raises(ValueError):
        validate_image_url("https://evil.com/pets/a.jpg")


def test_userinfo_로_허용_호스트를_흉내내는_우회를_막는다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`https://<허용호스트>@evil.com` 은 startswith 검사를 통과하지만 실제
    접속 대상은 evil.com 이다. hostname 파싱으로 막아야 한다."""
    _set_host(monkeypatch, "https://cdn.example.com")
    with pytest.raises(ValueError):
        validate_image_url("https://cdn.example.com@evil.com/pets/a.jpg")


def test_S3_미설정_로컬은_경고만_남기고_통과(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "", environment="local")
    url = "https://anything.example/x.jpg"
    assert validate_image_url(url) == url


def test_S3_미설정_비로컬은_절대URL을_거부(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_host(monkeypatch, "", environment="production")
    with pytest.raises(ValueError):
        validate_image_url("https://anything.example/x.jpg")

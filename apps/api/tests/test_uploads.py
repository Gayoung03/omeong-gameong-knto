"""공통 이미지 업로드 API 테스트."""

from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.endpoints import uploads
from app.core.config import settings
from app.main import app


class FakeS3Client:
    def __init__(self) -> None:
        self.upload: dict[str, object] | None = None

    def put_object(self, **kwargs: object) -> None:
        self.upload = kwargs


@pytest.fixture
def upload_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, FakeS3Client], None, None]:
    fake_s3 = FakeS3Client()
    monkeypatch.setattr(settings, "s3_bucket_name", "test-images")
    monkeypatch.setattr(settings, "s3_public_base_url", "https://images.example.com")
    monkeypatch.setattr(uploads, "_get_s3_client", lambda: fake_s3)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace()

    with TestClient(app) as client:
        yield client, fake_s3

    app.dependency_overrides.clear()


def test_upload_jpeg(upload_client: tuple[TestClient, FakeS3Client]) -> None:
    client, fake_s3 = upload_client
    image = b"\xff\xd8\xff\xe0test-image"

    response = client.post(
        "/api/v1/uploads",
        files={"file": ("ignored.exe", image, "application/octet-stream")},
        data={"purpose": "profile"},
    )

    assert response.status_code == 201
    assert response.json()["contentType"] == "image/jpeg"
    assert response.json()["sizeBytes"] == len(image)
    assert response.json()["fileUrl"].startswith("https://images.example.com/profile/")
    assert fake_s3.upload is not None
    assert fake_s3.upload["ContentType"] == "image/jpeg"
    assert fake_s3.upload["Body"] == image


def test_upload_rejects_fake_image(upload_client: tuple[TestClient, FakeS3Client]) -> None:
    client, fake_s3 = upload_client

    response = client.post(
        "/api/v1/uploads",
        files={"file": ("fake.jpg", b"not-an-image", "image/jpeg")},
        data={"purpose": "pet"},
    )

    assert response.status_code == 415
    assert fake_s3.upload is None


def test_upload_rejects_file_over_10mb(upload_client: tuple[TestClient, FakeS3Client]) -> None:
    client, fake_s3 = upload_client
    image = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024)

    response = client.post(
        "/api/v1/uploads",
        files={"file": ("large.png", image, "image/png")},
        data={"purpose": "profile"},
    )

    assert response.status_code == 413
    assert fake_s3.upload is None

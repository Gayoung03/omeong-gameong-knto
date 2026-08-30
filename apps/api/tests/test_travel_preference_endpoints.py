"""GET·PUT /users/me/travel-preference 통합 테스트."""

from fastapi.testclient import TestClient

_URL = "/api/v1/users/me/travel-preference"


def test_취향이_없으면_기본값_모양을_200으로_준다(client: TestClient) -> None:
    response = client.get(_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["companionCount"] == 1
    assert body["defaultPace"] is None
    assert body["defaultTransport"] is None
    assert body["preferredTags"] is None
    assert body["updatedAt"] is None


def test_PUT은_생성하고_GET으로_읽힌다(client: TestClient) -> None:
    response = client.put(
        _URL,
        json={
            "defaultPace": "normal",
            "defaultTransport": "own_car",
            "departureLocation": "서귀포시",
            "preferredDurationDays": 3,
            "companionCount": 2,
            "preferredTags": ["photo", "quiet"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["defaultPace"] == "normal"
    assert body["defaultTransport"] == "own_car"  # 값의 밑줄은 그대로
    assert body["companionCount"] == 2
    assert body["updatedAt"] is not None

    got = client.get(_URL).json()
    assert got["departureLocation"] == "서귀포시"
    assert got["preferredTags"] == ["photo", "quiet"]


def test_PUT은_전체_덮어쓰기다(client: TestClient) -> None:
    client.put(
        _URL,
        json={"defaultPace": "relaxed", "companionCount": 3, "departureLocation": "제주시"},
    )

    # 일부만 다시 보내면 나머지는 기본값으로 덮인다(PUT 전체 덮어쓰기).
    response = client.put(_URL, json={"defaultPace": "packed"})

    body = response.json()
    assert body["defaultPace"] == "packed"
    assert body["departureLocation"] is None  # 덮어써져 사라짐
    assert body["companionCount"] == 1  # 안 보내면 기본 1


def test_동반_인원과_기간은_1미만이면_422(client: TestClient) -> None:
    assert client.put(_URL, json={"companionCount": 0}).status_code == 422
    assert client.put(_URL, json={"preferredDurationDays": 0}).status_code == 422

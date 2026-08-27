"""AI 챗봇 대화·메시지 API 테스트.

메시지를 만드는 엔드포인트(SSE 스트리밍)는 아직 없다. 조회 쪽이 제대로
동작하는지 보려면 `chat_messages` 를 **DB 에 직접 넣어야** 한다.
"""

import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import ChatConversation, ChatMessage, Place, User
from app.db.models.enums import MessageRole
from app.services.chat_access import MAX_CONVERSATIONS, PREVIEW_LENGTH
from tests.conftest import KST


def _create(client: TestClient, **changes: object) -> dict:
    response = client.post("/api/v1/chat/conversations", json=dict(changes))
    assert response.status_code == 201, response.text
    return response.json()


def _add_message(
    db: Session,
    conversation_id: uuid.UUID,
    content: str,
    *,
    role: MessageRole = MessageRole.USER,
    minutes: int = 0,
    place_ids: list[uuid.UUID] | None = None,
    model_name: str | None = None,
) -> ChatMessage:
    """메시지를 직접 심는다. `created_at` 을 지정해 정렬을 검사할 수 있게 했다."""
    message = ChatMessage(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        referenced_place_ids=place_ids,
        model_name=model_name,
        created_at=datetime(2026, 8, 27, 14, 0, tzinfo=KST) + timedelta(minutes=minutes),
    )
    db.add(message)
    db.flush()
    return message


def test_대화를_만들면_제목없이_시작하고_계산값은_비어있다(client: TestClient) -> None:
    created = _create(client)

    assert created["title"] is None
    assert created["routeId"] is None
    # 201 응답에는 계산값이 없다 — 메시지가 없어 항상 같은 값이라서다.
    assert "messageCount" not in created

    detail = client.get(f"/api/v1/chat/conversations/{created['id']}").json()
    assert detail["messageCount"] == 0
    assert detail["lastMessagePreview"] is None


def test_목록은_최근에_이야기한_대화부터_준다(client: TestClient, db: Session) -> None:
    """`updated_at` 을 직접 심는다.

    PostgreSQL 의 `now()` 는 **트랜잭션 시작 시각**이라 테스트 안에서는 모든
    행이 같은 값을 받는다(테스트 전체가 트랜잭션 하나다). 엔드포인트를 불러
    갱신하는 방식으로는 순서를 만들 수 없다.
    """
    older = _create(client, title="예전 대화")
    newer = _create(client, title="최근 대화")

    base = datetime(2026, 8, 27, 14, 0, tzinfo=KST)
    for index, created in enumerate([older, newer]):
        conversation = db.get(ChatConversation, uuid.UUID(created["id"]))
        conversation.updated_at = base + timedelta(minutes=index)
    db.flush()

    body = client.get("/api/v1/chat/conversations").json()

    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [newer["id"], older["id"]]


def test_미리보기는_마지막_메시지를_스무자까지_보여준다(client: TestClient, db: Session) -> None:
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])

    answer = "애월 쪽에 강아지와 함께 실내까지 들어갈 수 있는 카페 세 곳을 찾았어요"
    _add_message(db, conversation_id, "애월 카페 알려줘", minutes=0)
    _add_message(db, conversation_id, answer, role=MessageRole.ASSISTANT, minutes=1)

    item = client.get("/api/v1/chat/conversations").json()["items"][0]

    assert item["messageCount"] == 2
    assert len(item["lastMessagePreview"]) == PREVIEW_LENGTH
    assert answer.startswith(item["lastMessagePreview"])


def test_미리보기는_system_메시지를_건너뛴다(client: TestClient, db: Session) -> None:
    """`system` 은 화면에 노출하지 않기로 한 역할이라 목록에도 뜨면 안 된다."""
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])

    _add_message(db, conversation_id, "사용자가 한 말", minutes=0)
    _add_message(db, conversation_id, "숨은 지시문", role=MessageRole.SYSTEM, minutes=1)

    item = client.get("/api/v1/chat/conversations").json()["items"][0]

    assert item["lastMessagePreview"] == "사용자가 한 말"
    # 개수에는 그대로 잡힌다 — 저장된 메시지가 맞기 때문이다.
    assert item["messageCount"] == 2


def test_메시지_목록은_오래된_순이고_장소를_펼쳐서_내려준다(
    client: TestClient, db: Session, place: Place
) -> None:
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])

    _add_message(db, conversation_id, "두번째로 온 말", minutes=5)
    _add_message(db, conversation_id, "먼저 온 말", minutes=0)
    _add_message(
        db,
        conversation_id,
        "여기 어때요",
        role=MessageRole.ASSISTANT,
        minutes=9,
        place_ids=[place.id],
        model_name="test-model",
    )

    body = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages").json()

    assert body["total"] == 3
    assert [item["content"] for item in body["items"]] == [
        "먼저 온 말",
        "두번째로 온 말",
        "여기 어때요",
    ]

    answer = body["items"][-1]
    assert answer["modelName"] == "test-model"
    assert [ref["id"] for ref in answer["referencedPlaces"]] == [str(place.id)]
    # 정책 행이 없는 장소도 5종 중 하나로 채워서 내려준다.
    assert answer["referencedPlaces"][0]["petPolicyType"] == "unknown"

    question = body["items"][0]
    assert question["modelName"] is None
    assert question["referencedPlaces"] == []


def test_사라진_장소는_referenced_places_에서_빠진다(
    client: TestClient, db: Session, place: Place
) -> None:
    """`referenced_place_ids` 는 외래키가 아니라 참조 무결성이 없다."""
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])
    _add_message(
        db,
        conversation_id,
        "장소 두 곳",
        role=MessageRole.ASSISTANT,
        place_ids=[place.id, uuid.uuid4()],
    )

    body = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages").json()

    assert [ref["id"] for ref in body["items"][0]["referencedPlaces"]] == [str(place.id)]


def test_대화를_지우면_메시지도_함께_지워진다(client: TestClient, db: Session) -> None:
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])
    _add_message(db, conversation_id, "지워질 말")

    assert client.delete(f"/api/v1/chat/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/api/v1/chat/conversations/{conversation_id}").status_code == 404
    assert db.get(ChatMessage, _any_message_id(db, conversation_id)) is None


def _any_message_id(db: Session, conversation_id: uuid.UUID) -> uuid.UUID:
    """CASCADE 확인용. 지워졌다면 조회 결과가 없으니 임의의 id 를 돌려준다."""
    message = db.query(ChatMessage).filter_by(conversation_id=conversation_id).first()
    return message.id if message else uuid.uuid4()


def test_다른_사용자의_대화는_열지도_고치지도_지우지도_못한다(
    client: TestClient, db: Session, stranger: User
) -> None:
    conversation = ChatConversation(id=uuid.uuid4(), user_id=stranger.id, title="남의 대화")
    db.add(conversation)
    db.flush()

    path = f"/api/v1/chat/conversations/{conversation.id}"
    assert client.get(path).status_code == 403
    assert client.patch(path, json={"title": "훔친 제목"}).status_code == 403
    assert client.delete(path).status_code == 403
    assert client.get(f"{path}/messages").status_code == 403


def test_없는_대화는_404다(client: TestClient) -> None:
    path = f"/api/v1/chat/conversations/{uuid.uuid4()}"
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"title": "제목"}).status_code == 404
    assert client.delete(path).status_code == 404


def test_목록에는_내_대화만_나온다(client: TestClient, db: Session, stranger: User) -> None:
    mine = _create(client)
    db.add(ChatConversation(id=uuid.uuid4(), user_id=stranger.id, title="남의 대화"))
    db.flush()

    body = client.get("/api/v1/chat/conversations").json()

    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [mine["id"]]


def test_남의_여행에는_대화를_붙일_수_없다(
    client: TestClient, db: Session, stranger: User
) -> None:
    from app.db.models import Route
    from app.db.models.enums import RouteCreationType, RouteStatus, TransportType, TripPace

    start = datetime(2026, 9, 11, 9, 0, tzinfo=KST)
    route = Route(
        id=uuid.uuid4(),
        user_id=stranger.id,
        title="남의 여행",
        status=RouteStatus.GENERATED,
        creation_type=RouteCreationType.MANUAL,
        start_at=start,
        end_at=start + timedelta(days=1),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(route)
    db.flush()

    response = client.post("/api/v1/chat/conversations", json={"routeId": str(route.id)})

    assert response.status_code == 403


def test_대화_상한을_넘으면_만들지_못한다(client: TestClient, db: Session, owner: User) -> None:
    """자동으로 지우지 않고 거부한다 — 사용자가 무엇을 버릴지 정한다."""
    db.add_all(
        ChatConversation(id=uuid.uuid4(), user_id=owner.id, title=f"대화 {index}")
        for index in range(MAX_CONVERSATIONS)
    )
    db.flush()

    response = client.post("/api/v1/chat/conversations", json={})

    assert response.status_code == 409
    assert str(MAX_CONVERSATIONS) in response.json()["detail"]


def test_제목_수정은_제목만_바꾼다(client: TestClient) -> None:
    conversation = _create(client, title="처음 제목")

    body = client.patch(
        f"/api/v1/chat/conversations/{conversation['id']}",
        json={"title": "서귀포 카페 찾기"},
    ).json()

    assert body["title"] == "서귀포 카페 찾기"
    assert body["id"] == conversation["id"]
    # 상세와 같은 스키마라 계산값도 함께 온다.
    assert body["messageCount"] == 0


def test_빈_제목은_거부한다(client: TestClient) -> None:
    conversation = _create(client)
    path = f"/api/v1/chat/conversations/{conversation['id']}"

    assert client.patch(path, json={"title": ""}).status_code == 422
    assert client.patch(path, json={}).status_code == 422

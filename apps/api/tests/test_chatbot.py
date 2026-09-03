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


def test_대화를_지우면_목록에서만_사라지고_메시지는_남는다(
    client: TestClient, db: Session
) -> None:
    """사용자가 지운 것은 "안 보이게 해달라"이지 "기록을 없애달라"가 아니다."""
    conversation = _create(client)
    conversation_id = uuid.UUID(conversation["id"])
    _add_message(db, conversation_id, "남아 있어야 할 말")

    assert client.delete(f"/api/v1/chat/conversations/{conversation_id}").status_code == 204

    assert client.get("/api/v1/chat/conversations").json()["total"] == 0
    assert db.query(ChatMessage).filter_by(conversation_id=conversation_id).count() == 1


def test_지운_대화는_열리지도_고쳐지지도_않는다(client: TestClient) -> None:
    """목록에서 사라졌는데 id 로는 열리면 "지운 것 같은데 왜 열리지"가 된다."""
    conversation = _create(client)
    path = f"/api/v1/chat/conversations/{conversation['id']}"
    assert client.delete(path).status_code == 204

    assert client.get(path).status_code == 404
    assert client.patch(path, json={"title": "새 제목"}).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.get(f"{path}/messages").status_code == 404


def test_지운_대화는_휴지통에서_볼_수_있다(client: TestClient) -> None:
    kept = _create(client, title="남길 대화")
    trashed = _create(client, title="지울 대화")
    client.delete(f"/api/v1/chat/conversations/{trashed['id']}")

    listed = client.get("/api/v1/chat/conversations").json()
    assert [item["id"] for item in listed["items"]] == [kept["id"]]

    trash = client.get("/api/v1/chat/conversations", params={"deleted": True}).json()
    assert trash["total"] == 1
    assert trash["items"][0]["id"] == trashed["id"]
    assert trash["items"][0]["title"] == "지울 대화"


def test_복구하면_목록의_원래_자리로_돌아온다(client: TestClient, db: Session) -> None:
    """`updated_at` 을 건드리지 않으므로 맨 위로 튀어 오르지 않는다."""
    older = _create(client, title="예전 대화")
    newer = _create(client, title="최근 대화")

    base = datetime(2026, 8, 27, 14, 0, tzinfo=KST)
    for index, created in enumerate([older, newer]):
        conversation = db.get(ChatConversation, uuid.UUID(created["id"]))
        conversation.updated_at = base + timedelta(minutes=index)
    db.flush()

    client.delete(f"/api/v1/chat/conversations/{older['id']}")

    # 지우는 것만으로 시각이 튀어도 안 된다 — updated_at 은 "마지막으로 이야기한 때"라서
    # 삭제·복구가 건드릴 값이 아니다(onupdate=now() 가 몰래 올리는 것을 막고 있다).
    trashed = db.get(ChatConversation, uuid.UUID(older["id"]))
    db.refresh(trashed)
    assert trashed.updated_at == base

    restored = client.post(f"/api/v1/chat/conversations/{older['id']}/restore")

    assert restored.status_code == 200
    assert restored.json()["id"] == older["id"]

    body = client.get("/api/v1/chat/conversations").json()
    assert [item["id"] for item in body["items"]] == [newer["id"], older["id"]]


def test_지우지_않은_대화는_복구할_수_없다(client: TestClient) -> None:
    conversation = _create(client)

    response = client.post(f"/api/v1/chat/conversations/{conversation['id']}/restore")

    assert response.status_code == 404


def test_지운_대화는_개수_상한에_잡히지_않는다(
    client: TestClient, db: Session, owner: User
) -> None:
    """"안 쓰는 대화를 지워주세요"라고 안내하므로, 지우면 실제로 자리가 나야 한다."""
    db.add_all(
        ChatConversation(id=uuid.uuid4(), user_id=owner.id, title=f"대화 {index}")
        for index in range(MAX_CONVERSATIONS)
    )
    db.flush()
    assert client.post("/api/v1/chat/conversations", json={}).status_code == 409

    victim = db.query(ChatConversation).filter_by(user_id=owner.id).first()
    assert client.delete(f"/api/v1/chat/conversations/{victim.id}").status_code == 204

    assert client.post("/api/v1/chat/conversations", json={}).status_code == 201


def test_자리가_없으면_복구를_거부한다(client: TestClient, db: Session, owner: User) -> None:
    """지운 사이에 대화를 상한까지 새로 만들었으면 되살릴 자리가 없다."""
    trashed = _create(client)
    assert client.delete(f"/api/v1/chat/conversations/{trashed['id']}").status_code == 204

    db.add_all(
        ChatConversation(id=uuid.uuid4(), user_id=owner.id, title=f"대화 {index}")
        for index in range(MAX_CONVERSATIONS)
    )
    db.flush()

    response = client.post(f"/api/v1/chat/conversations/{trashed['id']}/restore")

    assert response.status_code == 409
    assert str(MAX_CONVERSATIONS) in response.json()["detail"]


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
    # 남의 대화는 살아 있든 지워졌든 똑같이 403 이어야 상태를 캘 수 없다.
    assert client.post(f"{path}/restore").status_code == 403


def test_없는_대화는_404다(client: TestClient) -> None:
    path = f"/api/v1/chat/conversations/{uuid.uuid4()}"
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"title": "제목"}).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.post(f"{path}/restore").status_code == 404


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

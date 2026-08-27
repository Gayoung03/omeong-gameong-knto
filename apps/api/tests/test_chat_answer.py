"""챗봇 답변 생성 엔드포인트 테스트.

**OpenAI 를 부르지 않는다.** `generate_answer` 를 갈아끼워서 검사한다 —
진짜로 부르면 테스트마다 요금이 나가고, 답변이 매번 달라져 단언할 수가 없다.

모델이 실제로 어떤 인자를 고르는지는 여기서 검사할 수 없다. 그건 사람이
직접 물어보며 볼 부분이고, **고른 뒤의 동작**은 test_chat_place_search.py 에 있다.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import chatbot
from app.core.config import settings
from app.db.models import ChatConversation, ChatMessage, Place, User
from app.db.models.enums import MessageRole
from app.integrations.llm.chat import Answer, ChatGenerationError, ChatTimeoutError
from app.services.chat_access import KST


@pytest.fixture
def answering(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[list[dict]]]:
    """`generate_answer` 를 가짜로 바꾼다. 모델에게 간 대화 맥락을 기록해 둔다."""

    def install(
        content: str = "애월 쪽 카페 세 곳을 찾았어요.",
        place_ids: list[uuid.UUID] | None = None,
        error: Exception | None = None,
    ) -> list[list[dict]]:
        seen_history: list[list[dict]] = []

        def fake(db: Session, history: list[dict], question: str) -> Answer:
            seen_history.append(history)
            if error is not None:
                raise error
            return Answer(
                content=content,
                model_name="test-model",
                referenced_place_ids=place_ids or [],
            )

        monkeypatch.setattr(chatbot, "generate_answer", fake)
        return seen_history

    return install


def _conversation(client: TestClient) -> str:
    response = client.post("/api/v1/chat/conversations", json={})
    assert response.status_code == 201
    return response.json()["id"]


def _ask(client: TestClient, conversation_id: str, question: str = "애월 카페 알려줘"):
    return client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": question},
    )


def test_질문과_답변_두_행이_저장된다(
    client: TestClient, answering: Callable[..., list[list[dict]]]
) -> None:
    answering()
    conversation_id = _conversation(client)

    body = _ask(client, conversation_id).json()

    assert body["userMessage"]["role"] == "user"
    assert body["userMessage"]["content"] == "애월 카페 알려줘"
    assert body["assistantMessage"]["role"] == "assistant"
    assert body["assistantMessage"]["modelName"] == "test-model"

    listed = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages").json()
    assert listed["total"] == 2
    # 채팅 화면 순서대로 — 질문이 먼저다.
    assert [item["role"] for item in listed["items"]] == ["user", "assistant"]


def test_답변이_언급한_장소가_지도핀으로_내려간다(
    client: TestClient, db: Session, place: Place, answering: Callable[..., list[list[dict]]]
) -> None:
    answering(place_ids=[place.id])
    conversation_id = _conversation(client)

    answer = _ask(client, conversation_id).json()["assistantMessage"]

    assert [ref["id"] for ref in answer["referencedPlaces"]] == [str(place.id)]
    assert answer["referencedPlaces"][0]["name"] == place.name


def test_질문에는_지도핀이_붙지_않는다(
    client: TestClient, db: Session, place: Place, answering: Callable[..., list[list[dict]]]
) -> None:
    answering(place_ids=[place.id])
    conversation_id = _conversation(client)

    body = _ask(client, conversation_id).json()

    assert body["userMessage"]["referencedPlaces"] == []
    assert body["userMessage"]["modelName"] is None


def test_지난_대화가_맥락으로_함께_간다(
    client: TestClient, answering: Callable[..., list[list[dict]]]
) -> None:
    """되묻기("그 중에 주차 되는 데는?")가 되려면 앞의 대화를 함께 보내야 한다."""
    seen = answering()
    conversation_id = _conversation(client)

    _ask(client, conversation_id, "애월 카페 알려줘")
    _ask(client, conversation_id, "그 중에 주차 되는 데는?")

    # 첫 질문 때는 맥락이 비어 있고, 두 번째에는 앞의 질문·답변이 들어간다.
    assert seen[0] == []
    assert [message["role"] for message in seen[1]] == ["user", "assistant"]
    assert seen[1][0]["content"] == "애월 카페 알려줘"


def test_맥락은_최근_것부터_잘라서_보낸다(
    client: TestClient, db: Session, answering: Callable[..., list[list[dict]]]
) -> None:
    """앞에서부터 자르면 대화 초반만 남아 **방금 한 이야기를 모델이 못 본다.**"""
    seen = answering()
    conversation_id = _conversation(client)

    # `created_at` 을 직접 넣는다. 컬럼 기본값 now() 는 트랜잭션 시작 시각이라
    # 여기서 만든 30개가 **전부 같은 시각**을 받고, 그러면 "최근 20개"가 정해지지
    # 않는다. 엔드포인트는 실제 시각을 직접 넣으므로 이 문제가 없다.
    base = datetime(2026, 8, 27, 14, 0, tzinfo=KST)
    for index in range(30):
        db.add(
            ChatMessage(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(conversation_id),
                role=MessageRole.USER,
                content=f"질문 {index}",
                created_at=base + timedelta(minutes=index),
            )
        )
    db.flush()

    _ask(client, conversation_id, "마지막 질문")

    history = seen[0]
    assert len(history) == chatbot.HISTORY_LIMIT
    assert history[-1]["content"] == "질문 29"


def test_system_메시지는_맥락에서_빠진다(
    client: TestClient, db: Session, answering: Callable[..., list[list[dict]]]
) -> None:
    """시스템 프롬프트는 매번 새로 만들어 넣으므로 DB 것을 또 보내면 안 된다."""
    seen = answering()
    conversation_id = _conversation(client)
    db.add(
        ChatMessage(
            id=uuid.uuid4(),
            conversation_id=uuid.UUID(conversation_id),
            role=MessageRole.SYSTEM,
            content="숨은 지시문",
        )
    )
    db.flush()

    _ask(client, conversation_id)

    assert all(message["role"] != "system" for message in seen[0])


def test_실패하면_질문도_저장하지_않는다(
    client: TestClient, answering: Callable[..., list[list[dict]]]
) -> None:
    """실패한 질문만 쌓이면 다음 질문의 맥락이 어긋난다."""
    answering(error=ChatGenerationError("모델이 응답하지 않음"))
    conversation_id = _conversation(client)

    response = _ask(client, conversation_id)

    assert response.status_code == 502
    assert "다시 시도" in response.json()["detail"]

    listed = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages").json()
    assert listed["total"] == 0


def test_시간초과는_따로_구분된다(
    client: TestClient, answering: Callable[..., list[list[dict]]]
) -> None:
    answering(error=ChatTimeoutError("시간 초과"))
    conversation_id = _conversation(client)

    response = _ask(client, conversation_id)

    assert response.status_code == 504
    assert "늦어지고" in response.json()["detail"]


def test_빈_질문은_거부한다(client: TestClient) -> None:
    conversation_id = _conversation(client)

    assert _ask(client, conversation_id, "").status_code == 422
    assert (
        client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages", json={}
        ).status_code
        == 422
    )


def test_다른_사용자의_대화에는_질문할_수_없다(
    client: TestClient, db: Session, stranger: User
) -> None:
    conversation = ChatConversation(id=uuid.uuid4(), user_id=stranger.id, title="남의 대화")
    db.add(conversation)
    db.flush()

    assert _ask(client, str(conversation.id)).status_code == 403


def test_하루_상한을_넘기면_막는다(
    client: TestClient,
    db: Session,
    owner: User,
    monkeypatch: pytest.MonkeyPatch,
    answering: Callable[..., list[list[dict]]],
) -> None:
    """개발 중에는 세지 않으므로, 운영처럼 보이게 바꿔놓고 검사한다."""
    answering()
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "chat_daily_limit", 2)
    conversation_id = _conversation(client)

    assert _ask(client, conversation_id).status_code == 201
    assert _ask(client, conversation_id).status_code == 201
    blocked = _ask(client, conversation_id)

    assert blocked.status_code == 429
    assert "내일" in blocked.json()["detail"]


def test_개발환경에서는_상한을_세지_않는다(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, answering: Callable[..., list[list[dict]]]
) -> None:
    answering()
    monkeypatch.setattr(settings, "environment", "local")
    monkeypatch.setattr(settings, "chat_daily_limit", 1)
    conversation_id = _conversation(client)

    assert _ask(client, conversation_id).status_code == 201
    assert _ask(client, conversation_id).status_code == 201


def test_사라진_장소는_지도핀에서_빠진다(
    client: TestClient, db: Session, place: Place, answering: Callable[..., list[list[dict]]]
) -> None:
    """모델이 본 장소가 답변 저장 사이에 지워질 수 있다."""
    answering(place_ids=[place.id, uuid.uuid4()])
    conversation_id = _conversation(client)

    answer = _ask(client, conversation_id).json()["assistantMessage"]

    assert [ref["id"] for ref in answer["referencedPlaces"]] == [str(place.id)]


def test_질문을_보내면_대화_미리보기가_갱신된다(
    client: TestClient, answering: Callable[..., list[list[dict]]]
) -> None:
    answering(content="애월 쪽 카페 세 곳을 찾았어요.")
    conversation_id = _conversation(client)

    _ask(client, conversation_id)

    item = client.get("/api/v1/chat/conversations").json()["items"][0]
    assert item["messageCount"] == 2
    # 미리보기는 답변 앞부분이다. 마지막 메시지가 답변이므로 질문이 아니라 답변이 잡힌다.
    assert "애월 쪽 카페 세 곳을 찾았어요.".startswith(item["lastMessagePreview"])


def test_없는_대화에_질문하면_404다(client: TestClient) -> None:
    assert _ask(client, str(uuid.uuid4())).status_code == 404

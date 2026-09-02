"""대화 제목 서버 생성 (chatbot.md — "없으면 서버가 첫 질문에서 생성").

절단 규칙(순수 함수)과 SSE 첫 질문 시점의 저장 동작을 나눠 본다.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import chatbot as chatbot_endpoint
from app.integrations.llm.chat import Answer
from app.services.chat_access import TITLE_FALLBACK, derive_title

# ---------------------------------------------------------------------------
# derive_title — 절단 규칙
# ---------------------------------------------------------------------------


def test_짧은_질문은_그대로_제목이_된다() -> None:
    assert derive_title("서귀포 카페 알려줘") == "서귀포 카페 알려줘"


def test_개행과_연속_공백은_하나로_정리된다() -> None:
    assert derive_title("서귀포\n카페   알려줘") == "서귀포 카페 알려줘"


def test_길면_마지막_문장부호에서_자른다() -> None:
    text = "동쪽 바닷가 카페 어디가 좋을까? 강아지랑 같이 갈 건데 추천해줘"
    title = derive_title(text)
    assert title == "동쪽 바닷가 카페 어디가 좋을까?"
    assert len(title) <= 30


def test_문장부호가_없으면_마지막_공백에서_자른다() -> None:
    text = "제주 동부 해안도로 근처 반려동물 동반 가능한 브런치 맛집 추천"
    title = derive_title(text)
    assert len(title) <= 30
    assert not title.endswith(" ")
    assert text.startswith(title)


def test_경계가_없으면_하드_컷한다() -> None:
    text = "가" * 50
    assert derive_title(text) == "가" * 30


def test_경계가_너무_앞이면_하드_컷한다() -> None:
    # 문장부호가 3번째 글자에만 있으면 제목이 빈약해지므로 경계를 쓰지 않는다.
    text = "네? " + "가" * 40
    assert derive_title(text) == ("네? " + "가" * 40)[:30]


def test_공백뿐이면_폴백_제목이_된다() -> None:
    assert derive_title("   \n  ") == TITLE_FALLBACK


# ---------------------------------------------------------------------------
# POST /chat/conversations/{id}/messages — 첫 질문 시점 저장
# ---------------------------------------------------------------------------


@pytest.fixture
def quick_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 을 부르지 않고 곧장 답변을 돌려준다. 푸시 발송도 막는다."""

    def fake_stream(db, history, question) -> Generator:
        yield Answer(content="네, 알려드릴게요.", model_name="test-model")

    monkeypatch.setattr(chatbot_endpoint, "stream_answer", fake_stream)
    monkeypatch.setattr(chatbot_endpoint, "send_pushes", lambda db, notification: None)


def _create_conversation(client: TestClient, **body: object) -> dict:
    response = client.post("/api/v1/chat/conversations", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _send_message(client: TestClient, conversation_id: str, content: str) -> None:
    with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": content},
    ) as response:
        assert response.status_code == 200
        response.read()


def _get_title(client: TestClient, conversation_id: str) -> str | None:
    response = client.get(f"/api/v1/chat/conversations/{conversation_id}")
    assert response.status_code == 200
    return response.json()["title"]


def test_제목_없는_대화의_첫_질문이_제목이_된다(
    quick_answer, client: TestClient, db: Session
) -> None:
    conversation = _create_conversation(client)
    assert conversation["title"] is None

    _send_message(
        client, conversation["id"], "동쪽 바닷가 카페 어디가 좋을까? 강아지랑 같이 갈 건데 추천해줘"
    )

    assert _get_title(client, conversation["id"]) == "동쪽 바닷가 카페 어디가 좋을까?"


def test_지정한_제목은_첫_질문이_덮지_않는다(
    quick_answer, client: TestClient, db: Session
) -> None:
    conversation = _create_conversation(client, title="아껴둔 제목")

    _send_message(client, conversation["id"], "서귀포 카페 알려줘")

    assert _get_title(client, conversation["id"]) == "아껴둔 제목"


def test_두_번째_질문은_제목을_바꾸지_않는다(
    quick_answer, client: TestClient, db: Session
) -> None:
    conversation = _create_conversation(client)
    _send_message(client, conversation["id"], "첫 질문이에요")

    _send_message(client, conversation["id"], "두 번째 질문은 완전히 다른 내용")

    assert _get_title(client, conversation["id"]) == "첫 질문이에요"
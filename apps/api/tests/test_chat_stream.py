"""SSE 스트리밍에서 OpenAI 조각을 모으는 부분 테스트.

**DB 도 OpenAI 도 부르지 않는다.** 가짜 클라이언트가 청크를 내보낸다.

여기서 보는 것은 `stream_answer` 가 **조각을 어떻게 모으느냐**다. 스트리밍은
비스트리밍과 모양이 다르다 — 도구 호출의 `arguments` 가 완성된 JSON 문자열로
한 번에 오지 않고 **여러 청크에 걸쳐 쪼개져** 온다. 이어 붙이기를 틀리면 도구가
조용히 "검색 조건을 읽지 못했습니다"를 돌려주고, 챗봇은 장소를 못 찾은 것처럼
답한다 — 에러 없이 답변 품질만 나빠져서 알아채기 어렵다.
"""

from types import SimpleNamespace

import pytest

from app.integrations.llm import chat
from app.integrations.llm.chat import (
    Answer,
    AnswerDelta,
    ChatGenerationError,
    stream_answer,
)


def _chunk(*, content: str | None = None, tool_calls: list | None = None) -> SimpleNamespace:
    """OpenAI 청크 하나. 실제 응답에서 우리가 읽는 필드만 흉내 낸다."""
    return SimpleNamespace(
        model="test-model",
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=tool_calls))],
    )


def _tool_piece(index: int, *, call_id=None, name=None, arguments=None) -> SimpleNamespace:
    return SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch):
    """`_client()` 를 가짜로 바꾼다. 라운드마다 내보낼 청크 목록을 받는다."""

    def install(rounds: list[list[SimpleNamespace]]) -> list[list[dict]]:
        sent: list[list[dict]] = []
        remaining = list(rounds)

        def create(*, model, messages, tools, stream):
            assert stream is True
            sent.append([dict(message) for message in messages])
            return iter(remaining.pop(0))

        completions = SimpleNamespace(create=create)
        monkeypatch.setattr(
            chat, "_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions))
        )
        return sent

    return install


def test_답변_조각이_오는_대로_나온다(fake_openai) -> None:
    fake_openai([[_chunk(content="서귀포 쪽 "), _chunk(content="카페 두 곳이요.")]])

    pieces = list(stream_answer(None, [], "서귀포 카페"))

    assert pieces[:-1] == [AnswerDelta("서귀포 쪽 "), AnswerDelta("카페 두 곳이요.")]
    assert isinstance(pieces[-1], Answer)
    assert pieces[-1].content == "서귀포 쪽 카페 두 곳이요."


def test_쪼개진_도구_인자를_이어_붙인다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """`arguments` 는 완성된 JSON 으로 오지 않는다. 조각을 그대로 넘기면 파싱이 깨진다."""
    dispatched: list[tuple[str, str]] = []

    def fake_dispatch(db, name, raw_arguments):
        dispatched.append((name, raw_arguments))
        return "[]", []

    monkeypatch.setattr(chat, "_dispatch", fake_dispatch)
    fake_openai(
        [
            [
                _chunk(tool_calls=[_tool_piece(0, call_id="call_1", name="search_places")]),
                _chunk(tool_calls=[_tool_piece(0, arguments='{"region":')]),
                _chunk(tool_calls=[_tool_piece(0, arguments='"서귀포시/모슬포"}')]),
            ],
            [_chunk(content="다 찾았어요.")],
        ]
    )

    pieces = list(stream_answer(None, [], "서귀포 카페"))

    assert dispatched == [("search_places", '{"region":"서귀포시/모슬포"}')]
    # 도구 라운드는 화면에 보낼 것이 없다 — 답변 조각만 나가야 한다.
    assert pieces == [AnswerDelta("다 찾았어요."), pieces[-1]]
    assert isinstance(pieces[-1], Answer)


def test_한_라운드에_도구_두_개도_각각_모은다(
    fake_openai, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`index` 로 갈라 담지 않으면 두 호출의 인자가 한 덩어리로 섞인다."""
    dispatched: list[tuple[str, str]] = []

    def fake_dispatch(db, name, raw_arguments):
        dispatched.append((name, raw_arguments))
        return "[]", []

    monkeypatch.setattr(chat, "_dispatch", fake_dispatch)
    fake_openai(
        [
            [
                _chunk(
                    tool_calls=[
                        _tool_piece(0, call_id="a", name="search_places", arguments='{"region":'),
                        _tool_piece(1, call_id="b", name="search_guides", arguments='{"keywords":'),
                    ]
                ),
                _chunk(
                    tool_calls=[
                        _tool_piece(0, arguments='"중문"}'),
                        _tool_piece(1, arguments='["준비물"]}'),
                    ]
                ),
            ],
            [_chunk(content="정리했어요.")],
        ]
    )

    list(stream_answer(None, [], "중문 카페랑 준비물"))

    assert dispatched == [
        ("search_places", '{"region":"중문"}'),
        ("search_guides", '{"keywords":["준비물"]}'),
    ]


def test_빈_답변은_실패로_본다(fake_openai) -> None:
    """조각이 하나도 없으면 말풍선이 빈 채로 남는다. 재시도를 띄우는 편이 낫다."""
    fake_openai([[_chunk(content="")]])

    with pytest.raises(ChatGenerationError):
        list(stream_answer(None, [], "애월 카페"))


def test_도구만_반복하면_포기한다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """막지 않으면 검색만 반복하며 요금을 쓴다."""
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    fake_openai(
        [
            [_chunk(tool_calls=[_tool_piece(0, call_id="a", name="search_places", arguments="{}")])]
            for _ in range(chat.MAX_TOOL_ROUNDS)
        ]
    )

    with pytest.raises(ChatGenerationError):
        list(stream_answer(None, [], "애월 카페"))


def test_중지하면_다음_라운드로_가지_않는다(fake_openai) -> None:
    """제너레이터를 닫는 것이 앱의 중지 버튼이다. 남은 청크를 더 받지 않아야 한다."""
    fake_openai([[_chunk(content="서귀포 "), _chunk(content="쪽 카페")]])

    stream = stream_answer(None, [], "서귀포 카페")
    assert next(stream) == AnswerDelta("서귀포 ")
    stream.close()

    # 닫힌 제너레이터는 더 내놓지 않는다 — 완성된 Answer 가 나오지 않는다.
    assert list(stream) == []

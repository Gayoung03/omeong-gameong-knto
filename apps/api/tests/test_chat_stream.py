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


def _search_call(arguments: str = "{}") -> SimpleNamespace:
    """검색 라운드 하나. 0라운드는 도구를 강제하므로 대부분의 테스트가 여기서 시작한다."""
    return _chunk(
        tool_calls=[_tool_piece(0, call_id="a", name="search_places", arguments=arguments)]
    )


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch):
    """`_client()` 를 가짜로 바꾼다. 라운드마다 내보낼 청크 목록을 받는다.

    돌려주는 것은 **라운드마다 우리가 보낸 인자**다. 받은 청크만 보면 모델이
    말로 때웠는지는 알 수 있어도 **우리가 말할 여지를 줬는지**는 못 본다.
    도구를 강제했는지(`tool_choice`)는 보낸 쪽에만 남는다.
    """

    def install(rounds: list[list[SimpleNamespace]]) -> list[dict]:
        calls: list[dict] = []
        remaining = list(rounds)

        def create(*, model, messages, tools, stream, tool_choice=None):
            assert stream is True
            calls.append(
                {
                    "messages": [dict(message) for message in messages],
                    "tools": tools,
                    "tool_choice": tool_choice,
                }
            )
            return iter(remaining.pop(0))

        completions = SimpleNamespace(create=create)
        monkeypatch.setattr(
            chat, "_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions))
        )
        return calls

    return install


def test_답변_조각이_오는_대로_나온다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """검색 라운드를 앞에 둔다 — 0라운드는 도구를 강제하므로 말이 나올 수 없다."""
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    fake_openai(
        [
            [_search_call()],
            [_chunk(content="서귀포 쪽 "), _chunk(content="카페 두 곳이요.")],
        ]
    )

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


def test_빈_답변은_실패로_본다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """조각이 하나도 없으면 말풍선이 빈 채로 남는다. 재시도를 띄우는 편이 낫다."""
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    fake_openai(
        [
            [_search_call()],
            [_chunk(content="")],
        ]
    )

    with pytest.raises(ChatGenerationError, match="빈 답변"):
        list(stream_answer(None, [], "애월 카페"))


def test_도구만_반복하면_포기한다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """막지 않으면 검색만 반복하며 요금을 쓴다."""
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    fake_openai([[_search_call()] for _ in range(chat.MAX_TOOL_ROUNDS)])

    with pytest.raises(ChatGenerationError):
        list(stream_answer(None, [], "애월 카페"))


# ---------------------------------------------------------------------------
# 8/31 사고("잠시만요, 찾아볼게요.")를 잡는 자리.
#
# **내용으로 필러를 가려내는 테스트는 일부러 쓰지 않았다.** `"잠시만요,
# 찾아볼게요."` 와 정상적인 무검색 답변은 글자만 봐서는 구분이 안 된다 —
# 그래서 판단을 **말한 뒤가 아니라 말하기 전으로** 옮긴다: 0라운드에 모델이
# 무엇을 고를 수 있었는지를 본다.
# ---------------------------------------------------------------------------


def test_첫_라운드는_말로_때울_수_없어야_한다(
    fake_openai, monkeypatch: pytest.MonkeyPatch
) -> None:
    """8/31 에 말투 규칙으로 두 번 싸우고 두 번 되돌린 사고다.

    `tool_calls` 와 `content` 는 한 메시지에 못 들어간다. 그래서 모델이 "말하기"를
    고르는 순간 **그 질문에서 검색은 영영 없다** — 프롬프트로 두 번 막았지만
    확률적으로 샜다(설계 결정 문서 8/31 두 항목).

    막을 자리는 프롬프트가 아니라 여기다. 0라운드에 `tool_choice="required"` 를
    보내면 "말하기"가 **선택지에서 사라진다.**

    강제를 무시하고 말이 나오는 경우까지 여기서 함께 본다. 그때는 그 말을 **버리고**
    다시 묻는다 — 화면에 한 번 나가면 앱이 타이핑으로 찍어서 되돌릴 수 없다.
    """
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    calls = fake_openai(
        [
            # 규약 위반: 도구를 강제했는데 말로 답했다.
            [_chunk(content="잠시만요, 찾아볼게요.")],
            [_search_call()],
            [_chunk(content="실내로 갈 만한 곳 두 곳이에요.")],
        ]
    )

    pieces = list(stream_answer(None, [], "비 오는 날 함께 갈 실내 관광지 추천해줘"))

    assert calls[0]["tool_choice"] == "required"
    # 필러는 화면에도(델타) 저장에도(Answer) 남지 않는다.
    assert AnswerDelta("잠시만요, 찾아볼게요.") not in pieces
    assert pieces[-1].content == "실내로 갈 만한 곳 두 곳이에요."


def test_챗봇에게_environment_를_보여주지_않는다() -> None:
    """고르는 순간 빈 결과가 되는 값이라 도구 스키마에서 뺐다(2026-09-01).

    `"실내/실외. 비 오는 날 질문 등에 쓴다"` 라고 적어 두었더니 GPT 가
    `"비 오는 날 실내 관광지"` 에 `category=attraction` 과 함께 골랐는데,
    **팀 DB 의 관광지 149곳 중 `environment='indoor'` 은 0곳이다.** 실내 관광지는
    `indoor_tourism` 태그에 들어 있고(챗봇이 닿는 것 27곳), `environment='indoor'`
    212곳은 174곳이 어휘에서 뺀 `etc` 다 — 두 신호가 서로 다른 곳을 가리킨다.

    `not_allowed` 를 `pet_policy` enum 에서 뺀 것과 같은 판단이다. 되살리려면
    **데이터를 먼저 맞춰야** 한다. 검색 함수에는 그대로 있다(앱 필터가 쓴다).
    """
    properties = chat.SEARCH_TOOL["function"]["parameters"]["properties"]

    assert "environment" not in properties
    # 실내 질문이 갈 곳은 남아 있어야 한다.
    assert "indoor_tourism" in properties["tags"]["items"]["enum"]


def test_도구를_강제해도_잡담과_제주_밖_질문에_길이_있다() -> None:
    """`tool_choice` 강제를 8/31 에 접었던 이유가 이것이다 — "잡담·제주 밖 질문이 깨진다".

    깨지는 이유는 강제 자체가 아니라 **검색 말고 고를 것이 없어서**다.
    부작용 없는 도구를 하나 두면 `"안녕"`·`"서울 맛집"`·의료 질문이 그리로 빠지고,
    강제해도 멀쩡하다. 기각 사유가 사라진다.
    """
    names = {tool["function"]["name"] for tool in chat.TOOLS}

    assert "answer_directly" in names


def test_검색을_건너뛰기로_했으면_바로_답을_쓰게_한다(fake_openai) -> None:
    """탈출구를 고른 뒤에도 `auto` 로 두면 잡담에 검색이 따라붙는다.

    `_dispatch` 를 갈아끼우지 않는다 — `answer_directly` 는 DB 를 건드리지 않으므로
    진짜 경로가 그대로 돈다.
    """
    calls = fake_openai(
        [
            [
                _chunk(
                    tool_calls=[
                        _tool_piece(
                            0,
                            call_id="a",
                            name="answer_directly",
                            arguments='{"reason":"out_of_scope"}',
                        )
                    ]
                )
            ],
            [_chunk(content="저는 제주 여행만 도와드릴 수 있어요.")],
        ]
    )

    pieces = list(stream_answer(None, [], "서울 맛집 알려줘"))

    assert calls[0]["tool_choice"] == "required"
    assert calls[1]["tool_choice"] == "none"
    assert pieces[-1].content == "저는 제주 여행만 도와드릴 수 있어요."


def test_라운드를_다_쓰면_가진_것으로_답한다(fake_openai, monkeypatch: pytest.MonkeyPatch) -> None:
    """반대쪽 끝도 거칠다.

    `MAX_TOOL_ROUNDS` 를 다 쓰면 검색 결과를 손에 들고도 `ChatGenerationError` 로
    끝나 사용자는 `"답변 생성에 실패했어요"` 만 본다. 마지막 라운드에
    `tool_choice="none"` 을 보내면 **가진 것으로 문장을 쓸 수밖에 없어** 그 경로가
    없어진다.
    """
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    rounds = [
        [_search_call()]
        for _ in range(chat.MAX_TOOL_ROUNDS - 1)
    ]
    rounds.append([_chunk(content="세 곳 찾았어요.")])
    calls = fake_openai(rounds)

    list(stream_answer(None, [], "애월 카페"))

    assert calls[-1]["tool_choice"] == "none"


def test_중지하면_다음_라운드로_가지_않는다(
    fake_openai, monkeypatch: pytest.MonkeyPatch
) -> None:
    """제너레이터를 닫는 것이 앱의 중지 버튼이다. 남은 청크를 더 받지 않아야 한다."""
    monkeypatch.setattr(chat, "_dispatch", lambda db, name, raw: ("[]", []))
    fake_openai(
        [
            [_search_call()],
            [_chunk(content="서귀포 "), _chunk(content="쪽 카페")],
        ]
    )

    stream = stream_answer(None, [], "서귀포 카페")
    assert next(stream) == AnswerDelta("서귀포 ")
    stream.close()

    # 닫힌 제너레이터는 더 내놓지 않는다 — 완성된 Answer 가 나오지 않는다.
    assert list(stream) == []

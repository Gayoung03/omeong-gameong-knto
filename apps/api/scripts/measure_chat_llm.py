"""챗봇 답변 생성 — 성능·비용·쿼리 정확도 측정 (실제 OpenAI 호출).

`chat_quality_check.py`가 "내용이 맞는지"(사람이 읽음)를 본다면, 이 스크립트는
**숫자로 잴 수 있는 것**— 첫 글자까지 걸린 시간, 전체 완료 시간, 라운드 수, 토큰,
비용, 도구 인자 —을 본다. 문항은 `chat_quality_check.py`의 것을 그대로 재사용한다
(정답 기준을 두 곳에 따로 관리하지 않는다).

## 시간은 두 개를 따로 잰다

엔드포인트가 SSE 로 조각을 흘려보내므로 **사용자가 기다리는 시간은 전체 완료가
아니라 첫 글자까지**다. 그래서 `generate_answer()`(조각을 버린다) 대신
`stream_answer()` 를 엔드포인트와 같은 길로 돌려 둘을 나눠 기록한다.

## 실제로 돈이 나간다

`generate_answer()`를 실제로 호출한다 — OpenAI 요금이 그대로 청구된다. `--repeat`를
올리기 전에 문항 수 × 모델 수 × repeat 가 몇 번인지 어림해 볼 것.

## DB 는 기본 설정(현재 dev RDS)을 그대로 쓴다

이 스크립트는 **쓰기를 하지 않는다** — `search_places`/`search_guides`/
`search_transport_rules` 는 전부 SELECT 뿐이라, `measure_scenarios.py`처럼 로컬
호스트로 제한할 이유가 없다. `settings.database_url`(루트 `.env`)이 가리키는 곳에
그대로 붙는다.

## 어떻게 토큰·비용을 재는가

`chat.py`(프로덕션)는 고치지 않는다. `chat_module.OpenAI`라는 **이름만** 이 스크립트
안에서 추적 래퍼로 바꿔치기한다(`_trace_dispatch`가 `_dispatch`를 바꿔치기하는 것과
같은 방식). 래퍼는 스트리밍 호출에 `stream_options={"include_usage": True}`를 얹어
보내고, 마지막에 오는 usage-only 청크(그 청크는 `choices`가 비어 있어 `chat.py`의
기존 루프가 이미 `continue`로 건너뛴다 — 화면 출력에는 영향이 없다)를 옆에서
가로채 기록한다.

## 쿼리 정확도 — 판정이 아니라 **의심 신호**다

베이스라인 점검(2026-09-12)에서 gpt-4o-mini 가 재현 가능하게 놓치는 걸 두 개 봤다.
사람이 매번 답을 읽지 않고도 좁힐 수 있어 여기 넣었다. **둘 다 오답률이 아니다** —
세는 방법이 문자열 대조뿐이라, 숫자를 그대로 "틀린 비율"로 옮기면 안 된다.

1. **무게 인자**(`정확`/`값틀림`/`누락`) — 질문이 반려동물 무게를 말했는데
   `search_transport_rules` 가 `pet_weight_kg` 을 제대로 실었는지. 무게를 실어야
   회사별 판정 문장이 함께 오고, 안 실으면 모델이 결론 없이 애매하게 답한다.
   **무게 대상이 모호하면 아예 판단하지 않는다**(`_pet_weight_in_question` 참고) —
   "기내 제한이 7kg인가요?" 의 7kg 은 반려동물 무게가 아니고, "강아지 6kg,
   케이지 2kg" 은 어느 쪽인지 가릴 수 없다.
2. **항목 누락 의심** — 조회된 운송사 중 **일부만** 답변에 이름이 나온 것. 빠진
   회사는 "안 되는 곳"으로 읽히므로 시스템 프롬프트가 "하나도 빠뜨리지 말라"고 못
   박은 자리다. 다만 회사명을 약칭으로 쓰면 누락으로 잡히고, 아무 회사도 언급하지
   않으면 오히려 통과한다(나열이 정답이 아닌 질문을 봐주려고 그렇게 두었다).
   **원문을 열어 확인해야 확정된다.**

    uv run python -m scripts.measure_chat_llm \
        [--set rules|guardrails|places] [--models gpt-4o-mini,gpt-4o] \
        [--repeat 1] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from openai import OpenAI as RealOpenAI

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.llm import chat as chat_module
from scripts.chat_quality_check import QUESTION_SETS, SET_HEADINGS, _trace_dispatch

KST = timezone(timedelta(hours=9))

#: 출처: https://developers.openai.com/api/docs/pricing (확인일 2026-09-12).
#: 자주 바뀌는 값이라 오래 쓰기 전에 다시 확인할 것 — 여기가 틀리면 비용 숫자가 전부 틀린다.
PRICING_USD_PER_1M = {
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
}

ANY_WEIGHT_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*kg")

#: 반려동물을 가리키는 말. 무게가 **누구 것인지** 가리는 데 쓴다.
PET_NOUNS = "강아지|고양이|반려동물|반려견|반려묘|대형견|중형견|소형견|아이|애기"

#: `강아지가 12kg`, `20kg 대형견` 둘 다 잡는다. 반려동물과 붙어 있는 무게만 본다.
WEIGHT_NEAR_PET_PATTERN = re.compile(
    rf"(?:{PET_NOUNS})[^.?!]{{0,12}}?(\d+(?:\.\d+)?)\s*kg"
    rf"|(\d+(?:\.\d+)?)\s*kg[^.?!]{{0,12}}?(?:{PET_NOUNS})"
)


def _record_usage(stream, sink: list) -> Iterator:
    """스트림을 그대로 흘려보내며 usage 청크만 옆에서 옮겨 담는다.

    제너레이터라 `.close()`가 자동으로 생긴다(파이썬 제너레이터 내장 기능) —
    `chat.py`의 `finally: close = getattr(stream, "close", None)` 가 이걸 그대로 부르면
    `finally` 절이 실행돼 진짜 스트림도 닫힌다.
    """
    try:
        for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                sink.append(usage)
            yield chunk
    finally:
        close = getattr(stream, "close", None)
        if close:
            close()


class _TrackedCompletions:
    def __init__(self, completions, sink: list) -> None:
        self._completions = completions
        self._sink = sink

    def create(self, **kwargs):
        if not kwargs.get("stream"):
            return self._completions.create(**kwargs)
        kwargs["stream_options"] = {"include_usage": True}
        return _record_usage(self._completions.create(**kwargs), self._sink)


class _TrackedChat:
    def __init__(self, chat, sink: list) -> None:
        self.completions = _TrackedCompletions(chat.completions, sink)


class _TrackedOpenAI:
    """`chat_module.OpenAI` 자리를 대신 차지하는 래퍼. 실제 호출은 그대로 위임한다."""

    def __init__(self, *args, **kwargs) -> None:
        self._real = RealOpenAI(*args, **kwargs)
        self.usage: list = []
        self.chat = _TrackedChat(self._real.chat, self.usage)


def _cost_usd(model: str, usage_list: list) -> float:
    prices = PRICING_USD_PER_1M.get(model)
    if prices is None or not usage_list:
        return 0.0
    prompt = sum(u.prompt_tokens for u in usage_list)
    completion = sum(u.completion_tokens for u in usage_list)
    cached = sum(
        (u.prompt_tokens_details.cached_tokens if u.prompt_tokens_details else 0) or 0
        for u in usage_list
    )
    uncached = max(prompt - cached, 0)
    return (
        uncached * prices["input"] + cached * prices["cached_input"] + completion * prices["output"]
    ) / 1_000_000


def _pet_weight_in_question(question: str) -> float | None:
    """질문이 **반려동물의 무게**를 분명히 말했을 때만 그 값을 돌려준다.

    숫자+kg 라고 다 반려동물 무게가 아니다. "기내 제한이 7kg인가요?" 의 7kg 은
    항공사 상한이고, "강아지 6kg, 케이지 2kg" 은 어느 쪽을 실어야 하는지 이
    스크립트가 가릴 수 없다. 그래서 **숫자가 하나뿐이고 그 숫자가 반려동물을
    가리키는 말 옆에 있을 때만** 판단한다. 나머지는 `None`(판단 보류)이다.

    좁게 잡는 쪽이 맞다 — 엉뚱한 숫자를 "빠뜨렸다"고 세면 그 지표를 못 믿게 된다.
    """
    if len(ANY_WEIGHT_PATTERN.findall(question)) != 1:
        return None
    match = WEIGHT_NEAR_PET_PATTERN.search(question)
    if match is None:
        return None
    return float(next(group for group in match.groups() if group))


def _weight_arg_status(question: str, trace: list[dict]) -> str | None:
    """무게 인자를 제대로 실었는지. `None` 이면 판단하지 않은 문항이다.

    키가 있는지만 보지 않고 **값까지 맞는지** 본다 — 12kg 질문에 다른 숫자를
    실으면 판정이 통째로 틀리는데, 키만 세면 그게 통과로 잡힌다.
    """
    expected = _pet_weight_in_question(question)
    if expected is None:
        return None
    calls = [step for step in trace if step["tool"] == "search_transport_rules"]
    if not calls:
        return None
    for step in calls:
        arguments = json.loads(step["args"] or "{}")
        if "pet_weight_kg" not in arguments:
            continue
        try:
            return "정확" if float(arguments["pet_weight_kg"]) == expected else "값틀림"
        except (TypeError, ValueError):
            return "값틀림"
    return "누락"


def _tool_result_names(trace: list[dict]) -> set[str]:
    """도구 결과에 등장한 **운송사 이름**을 모은다.

    장소와 가이드는 일부러 세지 않는다. 장소는 시스템 프롬프트가 "한 번 검색에 최대
    3곳"으로 **줄이라고 지시**하므로 빠지는 것이 정상이고, 가이드는 글 제목을 답변에
    그대로 옮길 이유가 없다. "하나도 빠뜨리지 말라"는 규칙이 붙은 것은 운송사뿐이다.
    """
    names: set[str] = set()
    for step in trace:
        if step["tool"] != "search_transport_rules":
            continue
        try:
            payload = json.loads(step["result"])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict):
            payload = payload.get("규정", [])
        if not isinstance(payload, list):
            continue
        for record in payload:
            if isinstance(record, dict) and record.get("carrier_name"):
                names.add(record["carrier_name"])
    return names


def _missing_items(content: str, trace: list[dict]) -> list[str]:
    """조회된 운송사 중 **일부만** 답변에 등장했을 때, 빠진 이름을 돌려준다.

    하나도 안 나온 경우는 세지 않는다 — 회사를 나열하지 않는 것이 정답인 질문이
    있다(견종 질문은 분류하지 말고 직접 확인을 권하는 것이 정답이다). 반대로 일부만
    나온 것은 "나열하다가 빠뜨렸다"는 뜻이라 의심할 값이 된다.
    """
    names = _tool_result_names(trace)
    missing = sorted(name for name in names if name not in content)
    if not names or len(missing) == len(names):
        return []
    return missing


@dataclass
class Measurement:
    question_id: int
    model: str
    run: int
    #: 첫 글자가 화면에 뜨기까지. 스트리밍이라 **사용자가 체감하는 속도는 이쪽**이다.
    first_token_seconds: float | None = None
    #: 답변이 끝까지 나오기까지.
    seconds: float = 0.0
    rounds: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    #: `정확` / `값틀림` / `누락` / `None`(무게 대상이 모호해 판단하지 않음)
    weight_arg: str | None = None
    #: 이름이 답변에 안 보인 운송사. **누락 의심**이지 오답 확정이 아니다.
    suspected_missing_items: list[str] = field(default_factory=list)
    #: 모델이 실제로 보낸 도구 인자. 의심 신호를 원문으로 확인하려면 이게 있어야 한다 —
    #: 없으면 확인하러 갈 때마다 다시 호출해서 또 요금을 낸다. 장소 질문의 지역·카테고리
    #: 인자가 맞는지도 지금은 여기를 사람이 읽어서 본다.
    tool_args: list[dict] = field(default_factory=list)
    #: 답변 원문. 같은 이유로 남긴다.
    answer: str | None = None
    error: str | None = None


@dataclass
class _Run:
    result: object
    trace: list[dict]
    usage: list
    seconds: float
    first_token_seconds: float | None


def _ask(db, model: str, question: str) -> _Run:
    """`stream_answer()` 를 직접 돌린다.

    `generate_answer()` 는 조각을 다 버리고 최종 답만 주므로 **첫 글자가 언제 떴는지를
    알 수 없다.** 엔드포인트는 SSE 로 조각을 그대로 흘려보내니, 사용자가 기다리는
    시간은 전체 완료가 아니라 첫 조각까지다. 그래서 여기서는 엔드포인트와 같은 길로
    돌려 두 시간을 따로 잰다.
    """
    trace: list[dict] = []
    traced, original_dispatch = _trace_dispatch(trace)
    chat_module._dispatch = traced
    settings.openai_model = model

    original_openai = chat_module.OpenAI
    holder: dict = {}

    def factory(*args, **kwargs):
        client = _TrackedOpenAI(*args, **kwargs)
        holder["client"] = client
        return client

    chat_module.OpenAI = factory

    result: object = chat_module.ChatGenerationError("답변을 받지 못했습니다")
    first_token_at: float | None = None
    started = time.perf_counter()
    try:
        for piece in chat_module.stream_answer(db, [], question):
            if isinstance(piece, chat_module.AnswerDelta):
                if first_token_at is None:
                    first_token_at = time.perf_counter()
            else:
                result = piece
    except Exception as error:  # noqa: BLE001 - 한 문항이 죽어도 나머지는 돌린다
        result = error
    finally:
        elapsed = time.perf_counter() - started
        chat_module._dispatch = original_dispatch
        chat_module.OpenAI = original_openai

    client = holder.get("client")
    return _Run(
        result=result,
        trace=trace,
        usage=client.usage if client else [],
        seconds=elapsed,
        first_token_seconds=(first_token_at - started) if first_token_at else None,
    )


def _measure(spec: dict, model: str, run: int, db) -> Measurement:
    got = _ask(db, model, spec["question"])
    usage = got.usage
    is_error = isinstance(got.result, Exception)
    measurement = Measurement(
        question_id=spec["id"],
        model=model,
        run=run,
        first_token_seconds=(
            round(got.first_token_seconds, 2) if got.first_token_seconds else None
        ),
        seconds=round(got.seconds, 2),
        rounds=len(usage),
        prompt_tokens=sum(u.prompt_tokens for u in usage),
        completion_tokens=sum(u.completion_tokens for u in usage),
        cached_tokens=sum(
            (u.prompt_tokens_details.cached_tokens if u.prompt_tokens_details else 0) or 0
            for u in usage
        ),
        cost_usd=_cost_usd(model, usage),
        tool_calls=len(got.trace),
        tool_args=[{"tool": step["tool"], "args": step["args"]} for step in got.trace],
        error=f"{type(got.result).__name__}: {got.result}" if is_error else None,
    )
    if not is_error:
        measurement.answer = got.result.content
        measurement.weight_arg = _weight_arg_status(spec["question"], got.trace)
        measurement.suspected_missing_items = _missing_items(got.result.content, got.trace)
    return measurement


def _print_report(question_set: str, measurements: list[Measurement]) -> None:
    title, _ = SET_HEADINGS[question_set]
    host = settings.database_url.split("@")[-1].split("/")[0]
    print(f"# {title} — 성능·비용·쿼리 정확도")
    print()
    print(f"실행: {datetime.now(KST):%Y-%m-%d %H:%M} KST · 대상 DB: `{host}`")
    print()
    header = (
        f"{'#':>3} {'모델':<14} {'회차':>4} {'첫글자':>7} {'완료':>6} {'라운드':>6} "
        f"{'prompt':>8} {'cached':>7} {'completion':>10} {'비용(USD)':>10} "
        f"{'무게인자':>8} {'항목누락의심'}"
    )
    print(header)
    print("-" * len(header))
    for m in measurements:
        first = f"{m.first_token_seconds:.2f}" if m.first_token_seconds else "-"
        flag_items = ",".join(m.suspected_missing_items) if m.suspected_missing_items else ""
        status = f"오류:{m.error}" if m.error else ""
        print(
            f"{m.question_id:>3} {m.model:<14} {m.run:>4} {first:>7} {m.seconds:>6.2f} "
            f"{m.rounds:>6} {m.prompt_tokens:>8} {m.cached_tokens:>7} {m.completion_tokens:>10} "
            f"{m.cost_usd:>10.5f} {m.weight_arg or '-':>8} {flag_items}{status}"
        )
    print()

    by_model: dict[str, list[Measurement]] = {}
    for m in measurements:
        by_model.setdefault(m.model, []).append(m)

    print("## 모델별 합계")
    print()
    print(
        f"{'모델':<14}{'문항':>5}{'첫글자':>8}{'완료':>7}{'라운드':>8}"
        f"{'질문당(USD)':>13}{'입력비용%':>10}"
    )
    for model, rows in by_model.items():
        n = len(rows)
        firsts = [r.first_token_seconds for r in rows if r.first_token_seconds]
        avg_first = f"{sum(firsts) / len(firsts):.2f}" if firsts else "-"
        total_cost = sum(r.cost_usd for r in rows)
        print(
            f"{model:<14}{n:>5}{avg_first:>8}{sum(r.seconds for r in rows) / n:>7.2f}"
            f"{sum(r.rounds for r in rows) / n:>8.2f}{total_cost / n:>13.6f}"
            f"{_input_cost_share(model, rows) * 100:>9.1f}%"
        )
    print()

    # 인자·항목은 **판정이 아니라 의심 신호**다. 세는 방식이 문자열 대조뿐이라
    # 오답률로 읽으면 안 된다 — 원문을 봐야 확정된다.
    print("## 쿼리 정확도 (의심 신호 — 원문 확인 필요)")
    print()
    print(
        f"{'모델':<14}{'무게인자 정확':>14}{'값틀림':>8}{'누락':>7}"
        f"{'판단보류':>10}{'항목누락의심':>14}"
    )
    for model, rows in by_model.items():
        counts = {"정확": 0, "값틀림": 0, "누락": 0}
        for row in rows:
            if row.weight_arg in counts:
                counts[row.weight_arg] += 1
        skipped = sum(1 for r in rows if r.weight_arg is None)
        suspected = sum(1 for r in rows if r.suspected_missing_items)
        print(
            f"{model:<14}{counts['정확']:>14}{counts['값틀림']:>8}{counts['누락']:>7}"
            f"{skipped:>10}{suspected:>14}"
        )
    print()
    print(f"전체 예상 비용: ${sum(m.cost_usd for m in measurements):.4f}")


def _input_cost_share(model: str, rows: list[Measurement]) -> float:
    """비용에서 입력이 차지하는 몫. **토큰 개수 비중과 다르다** — 출력 단가가 4배다."""
    prices = PRICING_USD_PER_1M.get(model)
    total = sum(r.cost_usd for r in rows)
    if prices is None or not total:
        return 0.0
    output_cost = sum(r.completion_tokens for r in rows) * prices["output"] / 1_000_000
    return (total - output_cost) / total


def main() -> None:
    parser = argparse.ArgumentParser(description="챗봇 성능·비용·쿼리 정확도 측정(실제 호출)")
    parser.add_argument(
        "--set",
        dest="question_set",
        choices=sorted(QUESTION_SETS),
        default="rules",
        help="rules / places / guardrails — 문항은 chat_quality_check.py 것을 그대로 쓴다",
    )
    parser.add_argument("--models", default="gpt-4o-mini,gpt-4o", help="쉼표로 구분")
    parser.add_argument("--repeat", type=int, default=1, help="문항마다 몇 번씩 돌릴지")
    parser.add_argument("--json", dest="json_path", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    models = [name.strip() for name in args.models.split(",") if name.strip()]
    questions = QUESTION_SETS[args.question_set]
    total_calls = len(questions) * len(models) * args.repeat
    print(
        f"문항 {len(questions)} × 모델 {len(models)} × repeat {args.repeat} "
        f"= 최대 {total_calls}번 실제 OpenAI 호출 (라운드 있으면 더 늘어남)",
        file=sys.stderr,
    )

    measurements: list[Measurement] = []
    with SessionLocal() as db:
        for spec in questions:
            for model in models:
                for run in range(1, args.repeat + 1):
                    sys.stderr.write(f"  [{spec['id']}] {model} · {run}/{args.repeat} … ")
                    sys.stderr.flush()
                    measurement = _measure(spec, model, run, db)
                    measurements.append(measurement)
                    first = (
                        f"{measurement.first_token_seconds:.1f}s→"
                        if measurement.first_token_seconds
                        else ""
                    )
                    sys.stderr.write(
                        f"{first}{measurement.seconds:.1f}s · ${measurement.cost_usd:.5f}"
                        f"{' · 오류' if measurement.error else ''}\n"
                    )

    _print_report(args.question_set, measurements)

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(
                [m.__dict__ for m in measurements],
                handle,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n→ {args.json_path}")


if __name__ == "__main__":
    main()

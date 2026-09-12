"""챗봇 답변 생성 — 성능·비용·쿼리 정확도 측정 (실제 OpenAI 호출).

`chat_quality_check.py`가 "내용이 맞는지"(사람이 읽음)를 본다면, 이 스크립트는
**숫자로 잴 수 있는 것**— 응답시간, 라운드 수, 토큰, 비용, 도구 인자/항목 누락 —을 본다.
문항은 `chat_quality_check.py`의 것을 그대로 재사용한다(정답 기준을 두 곳에 따로 관리하지 않는다).

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

## 쿼리 정확도 — 자동으로 잡는 두 가지

베이스라인 점검(2026-09-12)에서 gpt-4o-mini 가 재현 가능하게 놓치는 걸 두 개 봤다.
사람이 매번 답을 읽지 않고도 기계로 잡을 수 있어 여기 넣었다.

1. **인자 누락** — 질문에 `숫자+kg`가 있는데 `search_transport_rules` 호출 인자에
   `pet_weight_kg`이 없다. 무게를 넣어야 판정(가능/불가) 문장이 함께 오는데, 안 넣으면
   모델이 결론 없이 애매하게 답한다(설계 결정 A7과 반대 방향의 실패).
2. **항목 누락** — 조회된 운송사 중 **일부만** 답변에 이름이 나온 것. 다건 응답을
   요약하며 몇 곳을 빠뜨리는 경우다. 빠진 회사는 "안 되는 곳"으로 읽히므로
   시스템 프롬프트가 "하나도 빠뜨리지 말라"고 못 박은 자리다.

둘 다 **완전하지 않다** — 인자 누락은 숫자가 하나뿐인 질문에서만 신뢰할 수 있고(복수
숫자면 어느 것을 채워야 하는지 이 스크립트는 모른다), 항목 누락은 이름이 답변에
안 보여도 실제로는 다른 표기로 언급됐을 수 있다. 그래도 사람이 매번 다 읽는 것보다는
빠르게 의심 지점을 좁혀준다.

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

WEIGHT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*kg")


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


def _missing_weight_arg(question: str, trace: list[dict]) -> bool:
    """질문에 무게가 하나만 언급됐는데 `search_transport_rules` 인자에 안 실렸으면 True."""
    weights = WEIGHT_PATTERN.findall(question)
    if len(weights) != 1:
        return False  # 없거나 여러 개면(어느 걸 채워야 할지 모호) 판단하지 않는다
    calls = [step for step in trace if step["tool"] == "search_transport_rules"]
    if not calls:
        return False
    return all("pet_weight_kg" not in json.loads(step["args"] or "{}") for step in calls)


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
    seconds: float = 0.0
    rounds: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    weight_arg_missing: bool = False
    missing_items: list[str] = field(default_factory=list)
    error: str | None = None


def _ask(db, model: str, question: str) -> tuple[object | None, list[dict], list, float]:
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

    started = time.perf_counter()
    try:
        result: object = chat_module.generate_answer(db, [], question)
    except Exception as error:  # noqa: BLE001 - 한 문항이 죽어도 나머지는 돌린다
        result = error
    finally:
        elapsed = time.perf_counter() - started
        chat_module._dispatch = original_dispatch
        chat_module.OpenAI = original_openai

    client = holder.get("client")
    return result, trace, client.usage if client else [], elapsed


def _measure(spec: dict, model: str, run: int, db) -> tuple[Measurement, object | None]:
    result, trace, usage, seconds = _ask(db, model, spec["question"])
    is_error = isinstance(result, Exception)
    measurement = Measurement(
        question_id=spec["id"],
        model=model,
        run=run,
        seconds=round(seconds, 2),
        rounds=len(usage),
        prompt_tokens=sum(u.prompt_tokens for u in usage),
        completion_tokens=sum(u.completion_tokens for u in usage),
        cached_tokens=sum(
            (u.prompt_tokens_details.cached_tokens if u.prompt_tokens_details else 0) or 0
            for u in usage
        ),
        cost_usd=_cost_usd(model, usage),
        tool_calls=len(trace),
        error=f"{type(result).__name__}: {result}" if is_error else None,
    )
    if not is_error:
        measurement.weight_arg_missing = _missing_weight_arg(spec["question"], trace)
        measurement.missing_items = _missing_items(result.content, trace)
    return measurement, (None if is_error else result)


def _print_report(question_set: str, measurements: list[Measurement]) -> None:
    title, _ = SET_HEADINGS[question_set]
    host = settings.database_url.split("@")[-1].split("/")[0]
    print(f"# {title} — 성능·비용·쿼리 정확도")
    print()
    print(f"실행: {datetime.now(KST):%Y-%m-%d %H:%M} KST · 대상 DB: `{host}`")
    print()
    header = (
        f"{'#':>3} {'모델':<14} {'회차':>4} {'초':>6} {'라운드':>6} "
        f"{'prompt':>8} {'cached':>7} {'completion':>10} {'비용(USD)':>10} "
        f"{'인자누락':>8} {'항목누락'}"
    )
    print(header)
    print("-" * len(header))
    for m in measurements:
        flag_weight = "예" if m.weight_arg_missing else ""
        flag_items = ",".join(m.missing_items) if m.missing_items else ""
        status = f"오류:{m.error}" if m.error else ""
        print(
            f"{m.question_id:>3} {m.model:<14} {m.run:>4} {m.seconds:>6.2f} {m.rounds:>6} "
            f"{m.prompt_tokens:>8} {m.cached_tokens:>7} {m.completion_tokens:>10} "
            f"{m.cost_usd:>10.5f} {flag_weight:>8} {flag_items}{status}"
        )
    print()

    by_model: dict[str, list[Measurement]] = {}
    for m in measurements:
        by_model.setdefault(m.model, []).append(m)

    print("## 모델별 합계")
    print()
    print(
        f"{'모델':<14}{'문항수':>6}{'평균초':>8}{'평균라운드':>10}{'총비용(USD)':>12}{'인자누락':>8}{'항목누락있음':>10}"
    )
    for model, rows in by_model.items():
        n = len(rows)
        avg_seconds = sum(r.seconds for r in rows) / n
        avg_rounds = sum(r.rounds for r in rows) / n
        total_cost = sum(r.cost_usd for r in rows)
        weight_misses = sum(1 for r in rows if r.weight_arg_missing)
        item_misses = sum(1 for r in rows if r.missing_items)
        print(
            f"{model:<14}{n:>6}{avg_seconds:>8.2f}{avg_rounds:>10.2f}"
            f"{total_cost:>12.5f}{weight_misses:>8}{item_misses:>10}"
        )
    print()
    total_cost_all = sum(m.cost_usd for m in measurements)
    print(f"전체 예상 비용: ${total_cost_all:.4f}")


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
                    measurement, _ = _measure(spec, model, run, db)
                    measurements.append(measurement)
                    sys.stderr.write(
                        f"{measurement.seconds:.1f}s · ${measurement.cost_usd:.5f}"
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

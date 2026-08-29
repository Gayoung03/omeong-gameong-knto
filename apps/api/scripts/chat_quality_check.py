"""규정·가이드 질문 답변 품질 점검 — 같은 질문을 모델 두 개로 돌린다.

`OPENAI_MODEL` 을 `gpt-4o` 로 올릴지(설계 결정 C1) 회의에 **숫자로** 올리기 위한 도구다.
지금까지의 근거는 "mini 가 세 번 틀렸다" 일화 하나뿐이라, 비용이 오르는 결정을 받기에 모자란다.

프로덕션 코드는 고치지 않는다. 모델 설정과 도구 호출 기록만 이 안에서 갈아끼운다.

문항은 두 벌이고 **도는 DB 가 다르다.**

    make chat-check          # rules  — 규정·가이드 질문. 로컬(dev-local)
    make chat-check-places   # places — 장소 질문. 팀 RDS

**장소 질문을 로컬에서 돌리면 무조건 0건이다.** 씨앗 장소 4건의 `region` 이
챗봇 어휘 밖이라 어떤 지역 질문도 걸리지 않는다. 이걸 모르고 점검하면
"장소 추천이 다 안 된다"는 잘못된 결론이 나온다. 그래서 타깃을 나눴다.

규정·가이드는 로컬 씨앗에 문서 15편·규정 12건이 다 있어 로컬로 충분하다.

정답 기준은 `scripts/seed_guides.py` 의 값에서 그대로 가져왔다.
**판정은 사람이 한다.** 이 스크립트는 같은 조건으로 답을 모아줄 뿐이다.
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.llm import chat as chat_module

KST = timezone(timedelta(hours=9))

DEFAULT_MODELS = ["gpt-4o-mini", "gpt-4o"]

#: 전부 **회사·항로를 집지 않은 질문**이다. 8/28 에 배운 것 — 한 곳만 조회되는
#: 질문은 통과하고, 여러 건이 조회되는 질문에서 모델이 뭉갠다.
RULE_QUESTIONS = [
    {
        "id": 1,
        "tag": "회귀 · 8/28 오답 ①",
        "question": "강아지가 12kg인데 비행기로 제주도 데려갈 수 있을까요?",
        "expected": [
            "기내는 7곳 **전부 불가** — 상한이 가장 높은 곳도 9kg이다",
            "위탁으로 가능한 곳은 **4곳** — 대한항공·아시아나·진에어·에어부산",
            "제주항공·티웨이·이스타는 **위탁 제도가 없어** 이 무게로는 갈 수 없다",
        ],
        "trap": "7곳을 '모두 ~하다'로 묶는 것. 8/28 에 세 번 연속 실패한 지점이다.",
    },
    {
        "id": 2,
        "tag": "회귀 · 8/28 오답 ②③",
        "question": "항공사들 화물칸에 반려동물 실을 수 있나요?",
        "expected": [
            "7곳 중 **4곳만** 위탁이 있다 (대한항공·아시아나·진에어·에어부산)",
            "제주항공·티웨이·이스타는 위탁 **제도 자체가 없다**",
            "'위탁이 없다'를 **'기내 탑승 불가'로 뒤집지 않을 것** — 이 3곳은 기내는 된다",
        ],
        "trap": "위탁 없음 → 탑승 불가로 뒤집기. 8/28 오답 ③이 정확히 이것이었다.",
    },
    {
        "id": 3,
        "tag": "회귀 · 8/28 오답 ①(견종)",
        "question": "복서 데리고 제주도 갈 수 있나요?",
        "expected": [
            "**어느 쪽으로도 단정하지 않을 것** — `transport_restricted_breeds` 가 비어 있다",
            "'복서는 맹견'은 **오답** — 동물보호법 맹견 5종에도 우리 데이터에도 없다",
            "'문제없다'도 오답 — 단두종 위탁 제한이 걸릴 수 있다",
            "항공사에 직접 확인하라고 안내하는 것이 정답",
        ],
        "trap": "보수적인 오답도 오답이다. 8/28 에 '복서는 허용되지 않는 맹견'이라고 지어냈다.",
    },
    {
        "id": 4,
        "tag": "회귀 · 8/28 오답 ④",
        "question": "강아지랑 제주도 갈 때 무슨 서류 챙겨야 해요?",
        "expected": [
            "**답해야 한다** — 탑승·반입 서류와 절차는 의료가 아니라 규정이다",
            "가드레일이 여기서 발동하면 실패 (8/28 에 입도 서류 질문까지 막혔다)",
            "가이드 문서의 제주 입도 절차 내용이 나와야 한다",
        ],
        "trap": "'예방접종'이라는 말에 걸려 건강·의료 금지 규칙이 잘못 발동하는 것.",
    },
    {
        "id": 5,
        "tag": "신규 · 여객선 다건",
        "question": "20kg 대형견인데 배로 제주도 갈 수 있나요?",
        "expected": [
            "완도(한일고속)·진도(산타모니카) — **무게 제한 없음**, 가능",
            "목포(씨월드) — 객실 등급이 무게로 갈린다. 20kg은 **펫스위트룸**만",
            "삼천포(오션비스타) — 무게 기준 **확인 안 됨** (불가가 아니다)",
            "고흥 녹동(아리온) — **원칙적으로 동승 불가**",
        ],
        "trap": "녹동 불가를 빠뜨리고 '모든 항로 가능'으로 묶는 것. 항공 다건과 같은 구조.",
    },
    {
        "id": 6,
        "tag": "신규 · 여객선 다건",
        "question": "반려동물 데리고 탈 수 있는 제주행 배편 알려주세요.",
        "expected": [
            "동반 가능 항로는 **4개** — 완도·목포·진도·삼천포",
            "고흥 녹동은 **불가**로 구분해서 말해야 한다 (`cabin_allowed: False`)",
            "'확인 안 됨'과 '불가'를 섞지 말 것",
        ],
        "trap": "5개 항로를 전부 가능으로 묶는 것.",
    },
]


#: 2026-08-29 권역 보정(275곳) 뒤 재검증용. **팀 RDS 에서만 의미가 있다.**
#: 보정으로 `서귀포시/모슬포` 가 42곳 → 150곳 안팎, `제주시/제주국제공항` 이
#: 361곳 → 250곳 안팎이 됐다. 늘어난 쪽과 **줄어든 쪽을 함께** 본다.
PLACE_QUESTIONS = [
    {
        "id": 1,
        "tag": "보정 대상 · 서귀포",
        "question": "서귀포에서 강아지랑 갈 만한 카페 알려줘",
        "expected": [
            "보정 전에는 **2곳**뿐이었다. 여러 곳이 나와야 한다",
            "소개하는 장소가 실제로 서귀포에 있어야 한다",
        ],
        "trap": "여전히 한두 곳이면 보정이 검색에 반영되지 않은 것이다.",
    },
    {
        "id": 2,
        "tag": "보정 대상 · 서귀포",
        "question": "서귀포에 강아지랑 갈 수 있는 실내 장소 있어?",
        "expected": [
            "보정 전에는 **1곳**뿐이었다",
            "동반정책을 기본으로 넘기지 않으므로 후보가 넉넉해야 한다",
        ],
        "trap": "1곳이면 보정 전과 같다.",
    },
    {
        "id": 3,
        "tag": "역방향 회귀 · 제주시",
        "question": "제주시에 강아지랑 갈 카페 추천해줘",
        "expected": [
            "**제주시에서 274곳을 뺐다.** 그래도 정상적으로 답해야 한다",
            "소개하는 장소 주소에 **서귀포가 섞이면 안 된다**",
        ],
        "trap": "가장 중요한 문항. 빼는 쪽을 과하게 뺐으면 여기서 드러난다.",
    },
    {
        "id": 4,
        "tag": "회귀 · 안 건드린 권역",
        "question": "애월에서 강아지랑 갈 수 있는 카페 알려줘",
        "expected": ["보정과 무관한 권역이다. 전과 같아야 한다(4곳 이상)"],
        "trap": "여기가 달라졌으면 엉뚱한 것까지 옮긴 것이다.",
    },
    {
        "id": 5,
        "tag": "회귀 · 중문",
        "question": "중문 근처에 강아지랑 갈 만한 곳 있어?",
        "expected": [
            "중문 권역은 원래 맞게 분류돼 있었다(활성 25곳). 전과 같아야 한다",
            "상예동·색달동은 아직 `서귀포시/모슬포` 다 — 2단계 몫이라 지금은 정상",
        ],
        "trap": "중문이 비었으면 중문 장소까지 모슬포로 옮긴 것이다.",
    },
    {
        "id": 6,
        "tag": "다건 · 제주 전체",
        "question": "제주도에서 반려동물 동반되는 카페 추천해줘",
        "expected": [
            "보정 전에는 서귀포·중문이 **0건**이라 북쪽만 나왔다",
            "이제 남쪽 장소가 섞여 나오면 보정이 먹은 것이다",
        ],
        "trap": "권역을 여러 번 검색하는 질문이다. 답변이 여덟 문장을 넘지 않아야 한다(C3).",
    },
]

QUESTION_SETS = {"rules": RULE_QUESTIONS, "places": PLACE_QUESTIONS}


def _trace_dispatch(trace):
    """`_dispatch` 를 감싸 도구 호출을 기록한다. 원본은 그대로 부른다.

    답이 틀렸을 때 **모델이 지어낸 것인지, 도구가 잘못 건넨 것인지**를
    가르려면 모델이 실제로 받은 값을 봐야 한다. 8/28 에 도구가 결론 문장을
    완성해서 건넸는데도 모델이 반대로 쓴 일이 있었다.
    """
    original = chat_module._dispatch

    def traced(db, name, raw_arguments):
        result, hits = original(db, name, raw_arguments)
        trace.append(
            {
                "tool": name,
                "args": raw_arguments,
                "hits": len(hits),
                "result": result,
            }
        )
        return result, hits

    return traced, original


def _ask(db, model: str, question: str):
    """한 문항을 한 모델로. (답변, 도구기록, 초, 오류) 를 돌려준다."""
    trace: list[dict] = []
    traced, original = _trace_dispatch(trace)
    chat_module._dispatch = traced
    settings.openai_model = model

    started = time.perf_counter()
    try:
        answer = chat_module.generate_answer(db, [], question)
        return answer, trace, time.perf_counter() - started, None
    except Exception as error:  # noqa: BLE001 - 한 문항이 죽어도 나머지는 돌린다
        return None, trace, time.perf_counter() - started, error
    finally:
        chat_module._dispatch = original


def _print_trace(trace: list[dict]) -> None:
    if not trace:
        print("> 도구를 한 번도 부르지 않았습니다. **답을 지어냈을 가능성이 높습니다.**")
        print()
        return

    print(f"<details><summary>도구 호출 {len(trace)}회 — 모델이 실제로 받은 값</summary>")
    print()
    for step in trace:
        hits = f" · 장소 {step['hits']}건" if step["hits"] else ""
        print(f"**{step['tool']}** `{step['args']}`{hits}")
        print()
        print("```")
        body = step["result"]
        print(body if len(body) <= 1200 else body[:1200] + f"\n… (총 {len(body)}자)")
        print("```")
        print()
    print("</details>")
    print()


#: 문항 묶음마다 제목과 한 줄 설명이 다르다.
SET_HEADINGS = {
    "rules": (
        "규정 질문 답변 품질 점검",
        "전부 **회사·항로를 집지 않은 질문**이다. 한 곳만 조회되는 질문은 8/28 에도 통과했다.",
    ),
    "places": (
        "장소 질문 답변 품질 점검 — 권역 보정 재검증",
        "**팀 RDS 기준.** 로컬에서 돌리면 전부 0건이라 의미가 없다.",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="답변 품질 점검")
    parser.add_argument(
        "--set",
        dest="question_set",
        choices=sorted(QUESTION_SETS),
        default="rules",
        help="rules 규정·가이드(로컬) / places 장소(팀 RDS)",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="쉼표로 구분. 기본은 " + " / ".join(DEFAULT_MODELS),
    )
    args = parser.parse_args()

    models = [name.strip() for name in args.models.split(",") if name.strip()]
    questions = QUESTION_SETS[args.question_set]
    title, lead = SET_HEADINGS[args.question_set]
    now = datetime.now(KST)

    print(f"# {title}")
    print()
    print(f"실행: {now:%Y-%m-%d %H:%M} KST · 모델 {' / '.join(models)} · 문항 {len(questions)}개")
    print(f"대상 DB: `{urlparse(settings.database_url).hostname}`")
    print()
    print(lead)
    print()
    print("## 채점표")
    print()
    print("| # | 문항 | " + " | ".join(models) + " |")
    print("| --- | --- | " + " | ".join(["---"] * len(models)) + " |")
    for spec in questions:
        cells = " | ".join(["☐"] * len(models))
        print(f"| {spec['id']} | {spec['question']} | {cells} |")
    print()
    print("_판정은 각 문항의 '정답 기준'과 대조해서 직접 채웁니다._")
    print()

    with SessionLocal() as db:
        for spec in questions:
            print("---")
            print()
            print(f"## {spec['id']}. {spec['question']}")
            print()
            print(f"`{spec['tag']}`")
            print()
            print("**정답 기준**")
            print()
            for line in spec["expected"]:
                print(f"- {line}")
            print()
            print(f"**함정** — {spec['trap']}")
            print()

            for model in models:
                print(f"### {model}", flush=True)
                print()
                sys.stderr.write(f"  [{spec['id']}/{len(questions)}] {model} … ")
                sys.stderr.flush()

                answer, trace, seconds, error = _ask(db, model, spec["question"])

                if error is not None:
                    sys.stderr.write(f"실패 ({seconds:.1f}초)\n")
                    print(f"> ⚠️ 실패 — `{type(error).__name__}: {error}`")
                    print()
                    _print_trace(trace)
                    continue

                sys.stderr.write(f"{seconds:.1f}초\n")
                print(f"_응답 모델 `{answer.model_name}` · {seconds:.1f}초_")
                print()
                print(answer.content)
                print()
                _print_trace(trace)

    sys.stderr.write("\n완료\n")


if __name__ == "__main__":
    main()

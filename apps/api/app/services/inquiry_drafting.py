"""1:1 문의 답변 **초안**을 만든다.

임베딩 없이 DB 조회로만 맥락을 모은다(저장소 방침 — `app/rag/` 설명 참고).
`editorial_drafting.py` 와 같은 방식이다 — 1회 강제 tool call, 방어 파싱.

초안은 저장하지 않는다. 관리자가 화면에서 읽고 다듬어 직접 등록한다.
"""

import json
import re
from dataclasses import dataclass

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Inquiry
from app.rag.retrieval.guide_search import search_guides
from app.services import inquiries as inquiry_service

#: 문의 카테고리별 가이드 검색 시드 키워드. 문의 본문 토큰과 합쳐 쓴다.
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "account": ["계정", "로그인", "회원", "비밀번호"],
    "pet": ["반려동물", "반려견", "프로필"],
    "saved": ["저장", "즐겨찾기", "코스"],
    "schedule": ["일정", "코스", "루트", "추천"],
    "bug": [],
    "etc": [],
}

_STOPWORDS = {
    "그리고", "그런데", "하지만", "그래서", "저는", "제가", "너무", "정말",
    "합니다", "했어요", "해요", "이거", "그거", "인데", "에서", "으로", "관련",
    "문의", "부탁", "드립니다", "있어요", "없어요", "같아요",
}

_TOKEN_SPLIT = re.compile(r"[\s,.!?~·…()\[\]{}\"'“”‘’/\\-]+")

_SERVICE_FACTS = {
    "app_name": "오멍가멍",
    "summary": "제주 반려동물 동반 여행을 돕는 서비스",
    "features": [
        "반려동물 조건에 맞는 여행 코스 추천과 저장",
        "반려동물 프로필 관리",
        "여행 기록(사진·일기) 작성",
        "제주 안내견 캐릭터 챗봇 '혼디' 상담",
        "공지사항과 1:1 문의",
    ],
    "support_scope": (
        "고객지원은 사용자를 대신해 계정 조치(탈퇴·비밀번호 재설정 등)를 "
        "수행하지 않고 방법만 안내한다."
    ),
}

INQUIRY_SUPPORT_PROMPT = (
    "너는 오멍가멍 고객지원 상담원이다. **답변 본문만** 작성한다 — 인사말"
    "('OOO님 안녕하세요, 오멍가멍입니다')과 맺음말('감사합니다 / 오멍가멍 드림')은 "
    "시스템이 자동으로 붙이므로 절대 쓰지 않는다. 부드러운 해요체 존댓말로, 이모지와 과한 "
    "감탄사 없이 정중하고 간결하게(2~5문장) 답한다. 제공된 맥락(과거 답변·가이드 "
    "문서·서비스 사실)에 없는 사실·날짜·수치·정책은 절대 지어내지 않는다. 맥락만으로 "
    "확실히 답할 수 없으면 사과하고 담당자가 확인 후 다시 답변드리겠다고 안내하며 "
    "needs_human_review 를 true 로 둔다. 계정 조치를 대신 해주겠다고 약속하지 말고 "
    "방법만 알려준다. 본문 첫 문장은 공감이나 확인으로 시작하고, 본문 마지막 문장은 "
    "해결되지 않으면 다시 문의해 달라는 안내로 맺는다. 반려동물 건강·의료 관련은 "
    "수의사 상담을 권한다. 이 답변은 관리자가 검토한 뒤 전송하는 초안이다."
)


@dataclass(frozen=True)
class InquiryDraft:
    reply: str
    used_context: list[str]
    needs_human_review: bool
    model: str


def _json_list(value: object) -> list:
    """모델이 배열 인자를 JSON 문자열로 감싸도 배열로 복구한다."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [value]
    return value if isinstance(value, list) else []


def _keywords(inquiry: Inquiry) -> list[str]:
    seeds = list(_CATEGORY_KEYWORDS.get(inquiry.category, []))
    tokens: list[str] = []
    for raw in _TOKEN_SPLIT.split(f"{inquiry.title} {inquiry.content}"):
        token = raw.strip()
        if len(token) >= 2 and token not in _STOPWORDS and token not in tokens:
            tokens.append(token)
    return list(dict.fromkeys(seeds + tokens))[:8]


def _past_answers(db: Session, inquiry: Inquiry) -> list[dict]:
    rows = db.execute(
        select(Inquiry.title, Inquiry.content, Inquiry.answer)
        .where(
            Inquiry.category == inquiry.category,
            Inquiry.status == "completed",
            Inquiry.answer.is_not(None),
            Inquiry.id != inquiry.id,
        )
        .order_by(Inquiry.answered_at.desc())
        .limit(3)
    ).all()
    return [
        {
            "title": title[:200],
            "content": content[:500],
            "answer": (answer or "")[:800],
        }
        for title, content, answer in rows
    ]


def _guides(db: Session, inquiry: Inquiry) -> list[dict]:
    hits = search_guides(db, keywords=_keywords(inquiry), limit=3)
    return [
        {
            "title": hit.title,
            "body": hit.body[:800],
            "sources": [name for name, _url in hit.sources],
        }
        for hit in hits
    ]


def _draft_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "write_support_reply",
            "description": "주어진 맥락만 사용해 1:1 문의 답변 초안을 작성한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": (
                            "고객에게 보낼 답변 **본문만**. 인사말·맺음말 없이 "
                            "부드러운 해요체."
                        ),
                    },
                    "used_context": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "참고한 가이드 제목 또는 과거 답변 요지. 없으면 빈 배열.",
                    },
                    "needs_human_review": {
                        "type": "boolean",
                        "description": "맥락만으로 확실히 답할 수 없으면 true.",
                    },
                },
                "required": ["reply", "needs_human_review"],
                "additionalProperties": False,
            },
        },
    }


def draft_answer(db: Session, inquiry: Inquiry) -> InquiryDraft:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")

    model = settings.inquiry_openai_model or settings.openai_model
    context = {
        "inquiry": {
            "category": inquiry.category,
            "title": inquiry.title,
            "content": inquiry.content,
        },
        "past_answers": _past_answers(db, inquiry),
        "guides": _guides(db, inquiry),
        "service_facts": _SERVICE_FACTS,
    }
    completion = OpenAI(
        api_key=settings.openai_api_key,
        timeout=30,
        max_retries=1,
    ).chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": INQUIRY_SUPPORT_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        tools=[_draft_tool()],
        tool_choice={"type": "function", "function": {"name": "write_support_reply"}},
    )
    calls = completion.choices[0].message.tool_calls
    if not calls:
        raise RuntimeError("답변 초안을 생성하지 못했습니다")

    data = json.loads(calls[0].function.arguments)
    body = str(data.get("reply") or "").strip()[:2000]
    if not body:
        raise RuntimeError("생성된 초안이 비어 있습니다")

    # 모델은 본문만 만든다. 관리자가 편집기에서 그대로 쓰도록 머릿말·꼬릿말을 붙여 준다.
    full = (
        f"{inquiry_service.answer_header(inquiry.asker.nickname)}\n\n"
        f"{body}\n\n{inquiry_service.INQUIRY_ANSWER_FOOTER}"
    )
    return InquiryDraft(
        reply=full,
        used_context=[str(item)[:200] for item in _json_list(data.get("used_context"))[:10]],
        needs_human_review=bool(data.get("needs_human_review")),
        model=model,
    )

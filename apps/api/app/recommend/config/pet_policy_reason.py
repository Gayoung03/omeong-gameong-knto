"""`recommendationReason` 규칙 템플릿 (docs/api/routes.md "recommendationReason 조립 규칙").

동반 가능이 확실한(tier `verified`) 후보의 근거 문장을 `place_pet_policies` 스냅샷에서
규칙으로만 만든다. LLM 은 쓰지 않는다. `needs_check` 후보는 확인 필요 안내를 유지한다.

조립 형식: ``{조건 접두 }{동반 문장} · {출처 라벨} 기준{ (YYYY-MM-DD 확인)}{ · 유의사항}``
"""

from zoneinfo import ZoneInfo

from app.db.models.enums import DataProvider, PetPolicyType
from app.recommend.schemas import CandidateTier, PetPolicy

KST = ZoneInfo("Asia/Seoul")

#: needs_check(정책 없음·unknown) 후보·항목의 안내 문구.
NEEDS_CHECK_REASON = "동반 여부 확인 필요"

#: policy_type -> 동반 문장. not_allowed 는 후보에서 제외되어 문장을 만들지 않는다.
POLICY_SENTENCES: dict[PetPolicyType, str] = {
    PetPolicyType.INDOOR_ALLOWED: "실내외 동반 가능",
    PetPolicyType.OUTDOOR_ONLY: "야외 동반 가능",
    PetPolicyType.PARTIAL_ALLOWED: "일부 구역 동반 가능",
}

#: source -> 한글 출처 라벨. 정책 출처로 쓰지 않는 값(tmap·weather_api)은 폴백을 쓴다.
SOURCE_LABELS: dict[DataProvider, str] = {
    DataProvider.TOUR_API: "확인된 반려동물 동반 정보",
    DataProvider.KCISA: "한국문화정보원 반려동물 동반 정보",
    DataProvider.VISITJEJU: "비짓제주 정보",
    DataProvider.KAKAO: "카카오 로컬 정보",
    DataProvider.INTERNAL: "자체 확인 정보",
}
SOURCE_LABEL_FALLBACK = "제공 정보"

#: (조건 컬럼, 명사, 서술어). 고정 순서 — 같은 서술어끼리 · 로, 다른 서술어는 , 로 잇는다.
_CONDITIONS: tuple[tuple[str, str, str], ...] = (
    ("leash_required", "목줄", "착용"),
    ("muzzle_required", "입마개", "착용"),
    ("carrier_required", "케이지", "이용"),
)


def _condition_prefix(policy: PetPolicy) -> str:
    """참인 동반 조건을 ``목줄·입마개 착용 시`` 같은 접두로 만든다. 없으면 빈 문자열."""
    groups: list[list[str]] = []  # [[verb, noun, noun...], ...]
    for attr, noun, verb in _CONDITIONS:
        if getattr(policy, attr):
            if groups and groups[-1][0] == verb:
                groups[-1].append(noun)
            else:
                groups.append([verb, noun])
    if not groups:
        return ""
    parts = [f"{'·'.join(nouns)} {verb}" for verb, *nouns in groups]
    return ", ".join(parts) + " 시"


def _source_sentence(policy: PetPolicy) -> str:
    label = SOURCE_LABELS.get(policy.source, SOURCE_LABEL_FALLBACK)
    sentence = f"{label} 기준"
    if policy.verified_at is not None:
        sentence += f" ({policy.verified_at.astimezone(KST):%Y-%m-%d} 확인)"
    return sentence


def reason_for(policy: PetPolicy | None, tier: CandidateTier) -> str:
    """후보의 근거 문장. verified 는 동반 조건 + 출처 문장, 그 외는 확인 필요 안내."""
    if tier != CandidateTier.VERIFIED or policy is None:
        return NEEDS_CHECK_REASON
    companion = POLICY_SENTENCES.get(policy.policy_type)
    if companion is None:
        # verified 인데 문장 표에 없는 policy_type(방어적) — 확인 필요로 폴백.
        return NEEDS_CHECK_REASON
    prefix = _condition_prefix(policy)
    head = f"{prefix} {companion}" if prefix else companion
    reason = f"{head} · {_source_sentence(policy)}"
    if policy.caution_note:
        reason += f" · {policy.caution_note}"
    return reason

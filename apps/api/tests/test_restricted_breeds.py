"""운송 제한 견종 — 시드 데이터 정합(순수).

응답 노출 통합 테스트는 test_guides.py, apply 신뢰도 기록은
test_design_backlog_batches.py 에 있다(PR 경계 기준).

시드 원자료는 travel-guide-collection.md 전사본이다. 테스트는 전사가 문서의
명시 종수·고유 사실(도베르만은 제주항공뿐, 예시 목록은 티웨이·이스타뿐)과
어긋나지 않는지 굳힌다.
"""

from app.db.models.enums import BreedRestrictionScope, BreedRestrictionType
from scripts.seed_restricted_breeds import BREED_GROUPS, split_breeds

# ---------------------------------------------------------------------------
# 시드 데이터 정합 (순수)
# ---------------------------------------------------------------------------


def test_문서가_명시한_종수와_파싱_결과가_일치한다() -> None:
    for key, r_type, _scope, _example, declared, raw in BREED_GROUPS:
        names = split_breeds(raw)
        assert len(names) == len(set(names)), f"{key} {r_type}: 중복 견종"
        if declared is not None:
            assert len(names) == declared, (
                f"{key} {r_type}: 문서 명시 {declared}종 ≠ 파싱 {len(names)}종"
            )


def test_도베르만은_제주항공_확정_목록에만_있다() -> None:
    carriers_with_doberman = {
        key[0]
        for key, _t, _s, example, _d, raw in BREED_GROUPS
        if not example and any("도베르만" in name for name in split_breeds(raw))
    }
    assert carriers_with_doberman == {"제주항공"}


def test_예시_목록은_티웨이와_이스타뿐이다() -> None:
    example_carriers = {key[0] for key, _t, _s, example, _d, _raw in BREED_GROUPS if example}
    assert example_carriers == {"티웨이항공", "이스타항공"}


def test_단두종은_전부_위탁_구간_제한이다() -> None:
    # 단두종 제한의 근거가 "위탁 중 호흡 문제"라, 기내(cabin)·양쪽(both) 단두종이
    # 생기면 원문을 다시 봐야 한다.
    for key, r_type, scope, _example, _d, _raw in BREED_GROUPS:
        if r_type == BreedRestrictionType.BRACHYCEPHALIC:
            assert scope == BreedRestrictionScope.CARGO, f"{key}: 단두종인데 {scope}"

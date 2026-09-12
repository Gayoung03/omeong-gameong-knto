"""TourAPI 실시간 조회 결과와 DB 후보의 대조 — 원문은 저장하지 않는다.

`route_recommendation.generate_route` 가 쓴다. 이 모듈은 상위 orchestrator 를
import 하지 않는다(단방향).
"""

import uuid

from app.db.models.enums import DataProvider
from app.integrations.tour_api.kto import TourPlace
from app.recommend.common.geo import haversine_m
from app.recommend.schemas import Candidate, ScoredCandidate


def _normalized_title(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _match_tour_places(
    candidates: list[Candidate],
    candidate_names: dict[uuid.UUID, str],
    tour_places: list[TourPlace],
) -> set[uuid.UUID]:
    """원문을 저장하지 않고 제목과 좌표가 맞는 DB 장소 ID만 돌려준다."""

    by_title: dict[str, list[TourPlace]] = {}
    for place in tour_places:
        by_title.setdefault(_normalized_title(place.title), []).append(place)

    matched: set[uuid.UUID] = set()
    for candidate in candidates:
        title = _normalized_title(candidate_names.get(candidate.place_id, ""))
        same_title = by_title.get(title, []) if title else []
        if any(
            haversine_m((candidate.lat, candidate.lng), (place.latitude, place.longitude)) <= 500
            for place in same_title
        ) or any(
            haversine_m((candidate.lat, candidate.lng), (place.latitude, place.longitude)) <= 30
            for place in tour_places
        ):
            matched.add(candidate.place_id)
    return matched


def _with_tour_api_note(candidate: ScoredCandidate) -> ScoredCandidate:
    """TourAPI 실시간 대조에 성공한 후보에 확인 접미를 한 번만 붙인다(decision 6).

    출처가 이미 한국관광공사(tour_api)면 근거 문장이 관광공사를 언급하므로 겹쳐 붙이지
    않는다. 다른 출처(또는 확인 필요 후보)에만 실시간 확인 사실을 덧붙인다.
    """
    if candidate.pet_policy is not None and candidate.pet_policy.source == DataProvider.TOUR_API:
        return candidate
    return candidate.model_copy(
        update={"reason": f"{candidate.reason} · 최신 관광정보 확인"}
    )

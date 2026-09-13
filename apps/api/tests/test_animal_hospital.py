"""동물병원 안전망 선정 규칙 단위 테스트 (순수 함수)."""

import uuid

from app.services.animal_hospital import (
    HospitalCandidate,
    _bounding_box,
    is_24h,
    rank_hospitals,
)

ANCHOR = (33.5000, 126.5000)


def _candidate(name: str, lat: float, lng: float) -> HospitalCandidate:
    return HospitalCandidate(
        id=uuid.uuid4(), name=name, address=None, phone=None, latitude=lat, longitude=lng
    )


def test_is_24h_by_name_marker() -> None:
    assert is_24h("24시동물병원") is True
    assert is_24h("24시똑똑똑동물메디컬센터") is True
    assert is_24h("노형 꿈 동물병원") is False


def test_24h_sorted_before_closer_non_24h() -> None:
    near = _candidate("가까운 동물병원", 33.5045, 126.5000)  # ~0.5km
    farther_24h = _candidate("24시동물병원", 33.5090, 126.5000)  # ~1.0km

    result = rank_hospitals([ANCHOR], [near, farther_24h])

    assert [h.name for h in result] == ["24시동물병원", "가까운 동물병원"]
    assert result[0].is_24h is True
    assert result[1].is_24h is False


def test_out_of_radius_excluded() -> None:
    far = _candidate("먼 동물병원", 33.6000, 126.5000)  # ~11km > 5km

    assert rank_hospitals([ANCHOR], [far]) == []


def test_distance_is_minimum_over_anchors() -> None:
    anchors = [ANCHOR, (33.5090, 126.5000)]
    candidate = _candidate("동물병원", 33.5090, 126.5000)  # 두 번째 앵커와 동일 지점

    result = rank_hospitals(anchors, [candidate])

    assert result[0].distance_meters == 0


def test_limit_caps_results() -> None:
    candidates = [_candidate(f"동물병원{i}", 33.5000 + i * 0.001, 126.5000) for i in range(5)]

    result = rank_hospitals([ANCHOR], candidates, limit=3)

    assert len(result) == 3
    # 거리순 오름차순.
    assert [h.distance_meters for h in result] == sorted(h.distance_meters for h in result)


def test_bounding_box_contains_anchor_span() -> None:
    min_lat, max_lat, min_lng, max_lng = _bounding_box([ANCHOR], radius_m=5000.0)

    assert min_lat < ANCHOR[0] < max_lat
    assert min_lng < ANCHOR[1] < max_lng
    # 위도 5km 는 약 0.045도.
    assert (max_lat - ANCHOR[0]) > 0.04

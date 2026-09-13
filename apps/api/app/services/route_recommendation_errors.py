"""추천 생성·편집 경로 공용 예외.

여러 하위 모듈(inputs·replacements 등)이 같은 예외를 던지고, 엔드포인트는
`route_recommendation` 에서 re-export 된 이름으로 잡는다. 순환 import 를 피하려
예외만 이 리프 모듈에 둔다.
"""


class LocationResolutionError(RuntimeError):
    """DB 장소와 주소·장소명 모두에서 좌표를 얻지 못했다."""


class RecommendationGenerationError(RuntimeError):
    """추천 루트를 생성할 수 없다."""

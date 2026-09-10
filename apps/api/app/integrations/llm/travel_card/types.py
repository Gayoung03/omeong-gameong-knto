"""파이프라인이 주고받는 값과 네 가지 결말.

## 왜 예외가 아니라 반환값인가

실패 이유마다 앱이 해야 할 일이 다르다 — 다른 사진을 고르라거나, 다시 시도하라거나.
예외로 던지면 부르는 쪽이 예외 종류를 하나씩 잡아야 하고, 새 실패가 생길 때마다
분기가 는다. 결말을 값으로 두면 프론트가 `outcome` 하나로 갈라 처리한다.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class CardOutcome(StrEnum):
    """카드 만들기의 네 가지 결말."""

    OK = "ok"
    #: 올린 사진이 안전 판정에 걸렸다.
    BLOCKED_INPUT = "blocked_input"
    #: 이미지 파일 자체를 못 읽었다(포맷 불일치·손상·HEIC·용량 초과).
    UNREADABLE_IMAGE = "unreadable_image"
    #: 생성 쪽이 결과물을 안전상 거부했다.
    BLOCKED_OUTPUT = "blocked_output"
    #: 위 셋이 아닌 실패(네트워크·타임아웃·키 없음). 앱에는 "다시 시도"만 보여준다.
    FAILED = "failed"


class PhotoKind(StrEnum):
    """우리 서비스용 사진 분류.

    사람 기준(패션샷·단체사진)이 아니다. 반려동물이 주인공인 서비스지만
    **사용자는 무엇이든 올린다** — 풍경만 찍은 사진이 오히려 더 많을 수 있다.
    그래서 반려동물 유무가 첫 갈래다.
    """

    PET_SOLO = "pet_solo"
    PET_WITH_HUMAN = "pet_with_human"
    PET_WITH_PET = "pet_with_pet"
    SCENERY = "scenery"
    FOOD = "food"
    OBJECT = "object"
    OTHER = "other"

    @property
    def has_pet(self) -> bool:
        """강아지 일기의 화자 시점을 가르는 값."""
        return self in (PhotoKind.PET_SOLO, PhotoKind.PET_WITH_HUMAN, PhotoKind.PET_WITH_PET)


class WritingStyle(StrEnum):
    """`travel_logs.writing_style` 과 같은 값을 쓴다."""

    JEJU_DIALECT = "jeju_dialect"
    DOG_DIARY = "dog_diary"


@dataclass(frozen=True)
class PhotoAnalysis:
    """단계 1의 결과."""

    kind: PhotoKind
    #: 사진에 실제로 보이는 것들. 한국어. 추측한 것은 넣지 않는다.
    items: list[str]
    safe: bool
    #: 안전하지 않다고 본 사유. 영어 키워드.
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CardText:
    """카드에 얹을 글. 제목과 메모를 나눠 받는다.

    한 덩어리로 받아 "첫 줄을 제목으로 써라" 하면, 첫 줄이 제목 노릇을 못 하는 평범한
    메모가 된다(실측: "집사가 백 장은 찍었댕" 이 제목 자리에 왔다). 제목은 그날을
    한마디로 요약하는 다른 종류의 글이라 따로 받는다.
    """

    title: str
    memos: list[str]


@dataclass(frozen=True)
class ImageInput:
    """읽어들인 원본 사진."""

    data: bytes
    mime_type: str
    width: int
    height: int

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0


@dataclass
class CardResult:
    """부르는 쪽이 받는 것 전부.

    `outcome` 이 OK 일 때만 `png` 가 채워진다. `message` 는 그대로 화면에 띄울 수 있는
    한국어 안내다 — **사진을 탓하지 않는 톤으로 쓴다.** 음식·동물 클로즈업에서 안전
    판정 오탐이 잦아, 사용자는 멀쩡한 사진을 올리고도 거절당하는 경험을 한다.
    """

    outcome: CardOutcome
    message: str = ""
    png: bytes | None = None
    analysis: PhotoAnalysis | None = None
    title: str = ""
    memos: list[str] = field(default_factory=list)
    prompt: str = ""
    #: 단계 이름 → 소요 시간(초).
    timings: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.outcome is CardOutcome.OK

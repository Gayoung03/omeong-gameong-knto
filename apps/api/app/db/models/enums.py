"""Database enum definitions shared across domain models."""

from enum import StrEnum

from sqlalchemy import Enum as SqlEnum


def db_enum(enum_class: type[StrEnum], name: str) -> SqlEnum:
    """Persist StrEnum values instead of Python member names."""
    return SqlEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class AuthProvider(StrEnum):
    LOCAL = "local"
    KAKAO = "kakao"
    APPLE = "apple"
    GOOGLE = "google"


class ConsentType(StrEnum):
    """회원가입·설정에서 받는 동의 항목."""

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    AGE_14_OR_OVER = "age_14_or_over"
    MARKETING = "marketing"


class PetSpecies(StrEnum):
    """강아지·고양이 외에는 종 이름을 species_detail 에 직접 받는다."""

    DOG = "dog"
    CAT = "cat"
    OTHER = "other"


class PetSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class TripPace(StrEnum):
    RELAXED = "relaxed"
    NORMAL = "normal"
    PACKED = "packed"


class TransportType(StrEnum):
    RENTAL_CAR = "rental_car"
    OWN_CAR = "own_car"
    TAXI = "taxi"
    PUBLIC_TRANSPORT = "public_transport"
    WALK = "walk"
    FERRY = "ferry"
    AIRPLANE = "airplane"


class PlaceEnvironment(StrEnum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    MIXED = "mixed"


class PetPolicyType(StrEnum):
    INDOOR_ALLOWED = "indoor_allowed"
    OUTDOOR_ONLY = "outdoor_only"
    PARTIAL_ALLOWED = "partial_allowed"
    NOT_ALLOWED = "not_allowed"
    UNKNOWN = "unknown"


class DataProvider(StrEnum):
    TOUR_API = "tour_api"
    KCISA = "kcisa"
    VISITJEJU = "visitjeju"
    KAKAO = "kakao"
    TMAP = "tmap"
    WEATHER_API = "weather_api"
    INTERNAL = "internal"


class RouteStatus(StrEnum):
    GENERATING = "generating"
    GENERATED = "generated"
    SAVED = "saved"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    FAILED = "failed"


class RouteCreationType(StrEnum):
    RECOMMENDED = "recommended"
    MANUAL = "manual"


class ScheduleItemType(StrEnum):
    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    ACCOMMODATION = "accommodation"
    CUSTOM = "custom"


class WeatherCondition(StrEnum):
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    WINDY = "windy"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# 아래 셋은 travel_logs 의 CHECK 제약과 짝이다. 컬럼 타입은 문자열이라
# db_enum() 을 쓰지 않지만, 값을 여기 모아두면 스키마·검증이 제약과 어긋나지 않는다.
# 값을 고칠 때는 community.TravelLog 의 CheckConstraint 도 함께 고쳐야 한다.


class WritingStyle(StrEnum):
    """여행기록 이미지에 얹는 글 말투."""

    DOG_DIARY = "dog_diary"
    JEJU_DIALECT = "jeju_dialect"


class MomentMood(StrEnum):
    HAPPY = "happy"
    EXCITED = "excited"
    RELAXED = "relaxed"
    BITTERSWEET = "bittersweet"


class GenerationStatus(StrEnum):
    IDLE = "idle"
    UPLOADING = "uploading"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

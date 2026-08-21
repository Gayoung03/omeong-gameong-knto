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
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"
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

"""후보의 방문 시각을 영업시간·브레이크타임 안으로 맞춘다."""

from datetime import date, datetime, timedelta

from app.recommend.schemas import BusinessHour, ScoredCandidate

from .types import KST


def fit_visit(
    candidate: ScoredCandidate, arrival: datetime, day_end: datetime
) -> tuple[datetime, datetime] | None:
    hours = hours_for(candidate, arrival.date())
    if hours is not None and hours.is_closed:
        return None

    starts_at = arrival
    closes_at = day_end
    if hours is not None and hours.opens_at is not None and hours.closes_at is not None:
        starts_at = max(starts_at, datetime.combine(arrival.date(), hours.opens_at, KST))
        closes_at = min(closes_at, datetime.combine(arrival.date(), hours.closes_at, KST))

    duration = timedelta(minutes=candidate.average_stay_minutes)
    if hours is not None and hours.break_start_at is not None and hours.break_end_at is not None:
        break_start = datetime.combine(arrival.date(), hours.break_start_at, KST)
        break_end = datetime.combine(arrival.date(), hours.break_end_at, KST)
        if starts_at < break_end and starts_at + duration > break_start:
            starts_at = break_end

    ends_at = starts_at + duration
    return (starts_at, ends_at) if ends_at <= closes_at else None


def hours_for(candidate: ScoredCandidate, route_date: date) -> BusinessHour | None:
    # Python은 월요일=0, 추천 계약은 일요일=0이다.
    day_of_week = (route_date.weekday() + 1) % 7
    return next(
        (hour for hour in candidate.business_hours if hour.day_of_week == day_of_week), None
    )

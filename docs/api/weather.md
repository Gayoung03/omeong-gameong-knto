# 날씨 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `weather_snapshots`

---

## 개념 정리

날씨는 외부 제공처에서 받아 `weather_snapshots`에 저장한 **스냅샷**입니다.
API는 이 저장된 값을 읽어 내려줄 뿐, 요청마다 외부 API를 호출하지 않습니다.

`(region, forecast_at)`에 UNIQUE 제약이 있어 같은 지역·같은 시각의 예보는 한 행뿐입니다.

여행 일정의 일자별 날씨는 `route_days.weather_snapshot_id`로 연결되며,
[`routes.md`](./routes.md)의 상세 응답에 이미 포함됩니다. 이 문서의 엔드포인트는
홈 화면처럼 여행과 무관하게 날씨만 볼 때 씁니다.

### 값 표기 정정

앱 [`features/trips/types/trip.ts`](../../apps/mobile/src/features/trips/types/trip.ts)의
`WeatherCondition`이 DB와 어긋나 있어 확정 규약(#1)에 맞춰 정리합니다.

| 앱 현재 | 변경 후 | 비고 |
| --- | --- | --- |
| `'partlyCloudy'` | `'partly_cloudy'` | 값의 밑줄은 표기법이 아니라 값의 일부 |
| `windy` 없음 | `windy` 추가 | DB는 6종, 앱은 5종 |

[`features/home/types/home.ts`](../../apps/mobile/src/features/home/types/home.ts)의
`WeatherSummary.condition`은 `string`인데, enum으로 좁혀야 합니다.

```text
sunny  partly_cloudy  cloudy  rainy  snowy  windy
```

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/weather/current` | 현재 시점 날씨 | — |
| GET | `/weather/forecast` | 기간별 예보 | — |

날씨는 개인 정보가 아니므로 인증이 필요 없습니다.

---

## GET /weather/current

홈 화면 상단에 쓰는 현재 날씨입니다.

### 요청

```text
GET /api/v1/weather/current?region=제주시
GET /api/v1/weather/current?latitude=33.4996&longitude=126.5312
```

| 파라미터 | 필수 | 설명 |
| --- | --- | --- |
| `region` | 조건부 | `weather_snapshots.region` |
| `latitude` `longitude` | 조건부 | 좌표로 가장 가까운 지역을 찾음 |

둘 중 하나는 반드시 보내야 합니다. 좌표는 지역을 찾는 데만 쓰고 **저장하지 않습니다**
([DB 문서](../database/README.md)의 GPS 정책).

### 응답 `200`

```json
{
  "region": "제주시",
  "forecastAt": "2026-08-12T15:00:00+09:00",
  "condition": "partly_cloudy",
  "temperature": 28.5,
  "minTemperature": 24.0,
  "maxTemperature": 30.1,
  "precipitationProbability": 20,
  "humidity": 68,
  "windSpeed": 3.4,
  "sourceUpdatedAt": "2026-08-12T14:00:00+09:00"
}
```

`sourceUpdatedAt`은 제공처가 이 예보를 만든 시각입니다.
데이터가 오래됐을 때 앱이 "몇 시 기준"을 표시할 수 있도록 함께 내려줍니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 해당 지역의 저장된 예보가 없음 |
| 422 | `region`과 좌표를 둘 다 보내지 않음, 좌표 범위 초과 |

> **[확인 필요]** 앱의 `WeatherSummary`에는 `greeting`("좋은 아침이에요")과
> `tip`("산책하기 좋은 날씨예요") 필드가 있는데 **DB에 없습니다.**
> 서버가 날씨에 따라 만들어 내려줄지, 앱이 `condition`을 보고 문구를 고를지 정해야 합니다.
> 앱이 만드는 쪽이면 문구 변경에 배포가 필요 없어 유리합니다.
>
> `location` 필드도 앱에만 있는데, `region`을 그대로 쓰면 됩니다.

---

## GET /weather/forecast

일정 화면에서 여행 기간의 예보를 볼 때 씁니다.

### 요청

```text
GET /api/v1/weather/forecast?region=제주시&from=2026-09-10&to=2026-09-12
```

| 파라미터 | 필수 | 설명 |
| --- | --- | --- |
| `region` | 조건부 | 좌표와 택일 |
| `latitude` `longitude` | 조건부 | |
| `from` `to` | ✅ | 날짜 범위 |
| `granularity` | — | `daily`(기본) 또는 `hourly` |

### 응답 `200` — daily

```json
{
  "region": "제주시",
  "granularity": "daily",
  "items": [
    {
      "date": "2026-09-10",
      "condition": "sunny",
      "temperature": 27.5,
      "minTemperature": 22.0,
      "maxTemperature": 29.0,
      "precipitationProbability": 10,
      "humidity": 60,
      "windSpeed": 2.8
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

`daily`는 그날의 여러 스냅샷을 서버가 하루 단위로 요약한 값입니다.
`temperature`는 낮 최고 기준이고, `condition`은 그날을 대표하는 상태입니다.

### 응답 `200` — hourly

```json
{
  "region": "제주시",
  "granularity": "hourly",
  "items": [
    {
      "forecastAt": "2026-09-10T09:00:00+09:00",
      "condition": "sunny",
      "temperature": 24.0,
      "precipitationProbability": 10
    }
  ],
  "total": 24,
  "limit": 100,
  "offset": 0
}
```

앱의 `HourlyWeather`는 `time`을 `HH:mm` 문자열로 갖고 있는데,
API는 날짜를 포함한 `forecastAt`을 내려줍니다. 여러 날짜를 한 번에 조회하면
시각만으로는 구분되지 않기 때문입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 기간에 해당하는 예보가 하나도 없음 |
| 422 | `to`가 `from`보다 앞, 범위가 너무 넓음 |

기간 일부만 데이터가 있으면 있는 만큼만 돌려줍니다. 없는 날짜는 배열에서 빠집니다.
앱은 `items` 길이가 요청 기간과 다를 수 있음을 전제로 그려야 합니다.

> **[확인 필요]** 예보를 며칠까지 제공할지.
> 기상청 단기예보는 보통 3일이라 그보다 먼 여행은 날씨가 `null`이 됩니다.
> 일정 화면에서 이 경우를 어떻게 표시할지 정해야 합니다.

---

## 데이터 수집

수집은 API가 아니라 배치 작업입니다. `apps/api/app/workers/`에서 주기적으로
제공처를 호출해 `weather_snapshots`에 저장합니다.

이 문서의 엔드포인트는 저장된 값을 읽기만 합니다.
외부 호출을 요청 시점에 하지 않는 이유는 응답이 느려지고 제공처 호출량이 늘기 때문입니다.

> **[확인 필요]** 수집 주기와 보관 기간. 지난 예보를 언제까지 남길지 정해야 합니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |

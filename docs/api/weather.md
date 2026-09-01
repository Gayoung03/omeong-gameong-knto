# 날씨 API

작성일: 2026-08-12 · 갱신: 2026-08-31 · 상태: **홈 현재 날씨 구현 완료**

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `weather_snapshots`

---

## 개념 정리

홈 현재 날씨는 `WEATHER_API_KEY`를 사용해 기상청 단기예보를 조회합니다.
앱은 10분 동안 응답을 재사용하며, 키는 백엔드에만 둡니다.

여행 일정 날씨는 별도로 `weather_snapshots`에 저장하는 **스냅샷**입니다.

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
GET /api/v1/weather/current?region=제주
GET /api/v1/weather/current?region=한림
```

| 파라미터 | 필수 | 설명 |
| --- | --- | --- |
| `region` | ✅ | `제주` `서귀포` `한림` `성산` 중 하나 |

각 권역은 서버에 정의된 대표 좌표로 조회하며 사용자의 GPS는 받거나 저장하지 않습니다.

### 응답 `200`

```json
{
  "region": "제주",
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
| 422 | 지원하지 않는 지역 또는 `region` 누락 |
| 502 | 기상청 호출 실패 또는 불완전한 응답 |

### `greeting`·`tip`은 앱이 만듭니다 **[확정]** (2026-08-18)

앱의 `WeatherSummary`([`home/types/home.ts`](../../apps/mobile/src/features/home/types/home.ts))에는
`greeting`("안녕, 보호자님!")과 `tip`("바람이 많이 불어요...") 필드가 있는데 DB에 없습니다.

**둘 다 앱이 만듭니다. API 응답에 포함하지 않습니다.**

| 앱 필드 | 만드는 방법 |
| --- | --- |
| `greeting` | **날씨와 무관.** 시간대를 보고 고르거나 고정 문구 |
| `tip` | 응답의 `condition`·`windSpeed`·`precipitationProbability`를 보고 앱이 선택 |
| `location` | 응답의 `region`을 그대로 사용 |

`greeting`은 [`WeatherHero.tsx:32`](../../apps/mobile/src/features/home/components/WeatherHero.tsx)에서
캐릭터 옆 첫 줄로 그려지는 인사말이라 날씨 데이터가 아예 필요 없습니다.
`tip`도 수치만 있으면 앱이 고를 수 있습니다.

앱이 만들면 **문구를 바꿀 때 서버 배포가 필요 없습니다.**

> **`condition`은 영문 코드입니다.** 서버는 `partly_cloudy`를 내리고 앱이 "구름 많음"으로
> 바꿔 보여줍니다([`README.md`](./README.md) 7장 규약).
> 앱 목업 [`home.mock.ts`](../../apps/mobile/src/features/home/mocks/home.mock.ts)가
> `condition: '구름 많음'` 한글을 쓰고 있어 연동 시 혼동하기 쉽습니다.

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

### 예보는 3일까지 **[확정]** (2026-08-18)

**기상청 단기예보만 씁니다. 오늘부터 3일치입니다.**

```text
5박 6일 여행을 등록한 경우

1일차  ☀️     2일차  🌤️     3일차  🌧️      ← items 에 있음
4일차  —      5일차  —      6일차  —       ← items 에 없음
```

4일차 이후는 배열에서 빠지므로, 앱은 해당 날짜 칸을 "예보 준비 중"처럼 표시합니다.

**중기예보(3~10일)를 쓰지 않는 이유**

기상청 중기예보를 붙이면 10일까지 늘릴 수 있지만 데이터 성격이 달라집니다.

| | 단기예보 (3일) | 중기예보 (4~10일) |
| --- | --- | --- |
| 시간 단위 | 3시간 | 오전 / 오후 2번 |
| 습도 · 풍속 | 있음 | **없음** |
| 지역 단위 | 격자 좌표(약 5km) | 광역 구역 코드 |

지역을 찾는 방식이 격자 좌표와 구역 코드로 갈려 **매핑 테이블을 두 벌 관리**해야 하고,
응답 항목도 날짜에 따라 필드가 있다 없다 하게 됩니다.
여행 직전에 확인하는 용도라면 3일로 충분하다고 보고 단기예보만 씁니다.

나중에 중기예보를 붙일 때는 이 절과 `granularity` 처리만 고치면 됩니다.
`weather_snapshots`의 `humidity`·`wind_speed`가 nullable이라 **DB는 그대로 담을 수 있습니다.**

---

## 데이터 수집

수집은 API가 아니라 배치 작업입니다. `apps/api/app/workers/`에서 주기적으로
제공처를 호출해 `weather_snapshots`에 저장합니다.

이 문서의 엔드포인트는 저장된 값을 읽기만 합니다.
외부 호출을 요청 시점에 하지 않는 이유는 응답이 느려지고 제공처 호출량이 늘기 때문입니다.

### 주기와 보관 기간 **[확정]** (2026-08-18)

```text
수집 주기    1시간
보관 기간    7일  (지난 예보는 배치가 삭제)
```

기상청 단기예보는 3시간마다 새로 발표되지만, 1시간마다 확인하면 발표를 놓치지 않습니다.
매번 전체를 다시 받아도 **같은 시간대 예보는 덮어쓰기로 처리**됩니다.
`weather_snapshots`에 `(region, forecast_at)` UNIQUE 제약이 있어 upsert가 됩니다.

보관을 7일로 잡은 이유는 지난 날씨를 다시 볼 화면이 없기 때문입니다.
여행기록에 "그날 날씨"를 남기는 기능이 생기면 이 값을 다시 봐야 합니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-18 | 미정 3건 확정 — `greeting`·`tip`은 **앱이 생성**(응답에서 제외), 예보 **3일**(단기예보만, 중기예보 미채택 사유 기록), 수집 **1시간 간격 · 7일 보관** |

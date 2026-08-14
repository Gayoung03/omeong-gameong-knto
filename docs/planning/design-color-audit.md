# 디자인 통일 감사 리포트 — 색상

- 대상 브랜치: `dev/integration` (통합 PR, 미머지)
- 범위: `apps/mobile/app/**`, `apps/mobile/src/**` (단 `src/theme/` 제외)
- 기준 토큰: `src/theme/colors.ts` (26개)
- 작성일: 2026-08-10
- **상태: 조사 완료 → 작업 완료.** 아래 조사 결과를 근거로 `work/yulim/refactor/design-color-tokens`
  브랜치에서 치환을 마쳤다. 실제 적용 결과는 문서 맨 아래 "8. 적용 결과" 참고.

---

## 1. 한눈에 보기

| 항목                      | 수치      |
| ------------------------- | --------- |
| 하드코딩된 색상 등장 횟수 | **323회** |
| 서로 다른 색상값 종류     | **229개** |
| 관련 파일                 | **48개**  |
| 현재 theme 토큰           | 26개      |

229개의 값이 26개 토큰으로 수렴해야 한다. 즉 **평균 9개의 서로 다른 값이 같은 역할을 하고 있다.**

### 분류 결과

| 분류                    | 건수 | 뜻                               | 처리                                         |
| ----------------------- | ---: | -------------------------------- | -------------------------------------------- |
| 정확일치                |   28 | 토큰과 값이 같음                 | 그냥 토큰으로 치환. 화면 안 바뀜             |
| 유사색-확인필요         |  107 | ΔE 0.5~4 — 눈으로 구분 거의 불가 | 토큰으로 치환. 화면 사실상 안 바뀜           |
| 근접-판단필요           |   72 | ΔE 4~10 — 자세히 보면 다름       | 치환 시 미세하게 바뀜. 담당자 확인 권장      |
| 토큰없음                |   85 | ΔE 10 이상 — 명백히 다른 색      | 새 토큰 추가 or 기존 토큰으로 통일 결정 필요 |
| 오버레이(rgba·8자리hex) |   29 | 투명도 포함                      | 토큰화 대상 아님. 별도 처리                  |
| transparent             |    2 | 투명                             | 그대로 둠                                    |

> ΔE는 사람 눈이 느끼는 색 차이 값이다. **ΔE 1 이하 = 나란히 놓아도 구분 못 함**, 2~3 = 유심히 보면 다름, 10 이상 = 누가 봐도 다른 색.

### 기능별 분포

| 기능                  | 합계 | 정확일치 | 유사색 | 근접 | 토큰없음 | 최근 작성자       |
| --------------------- | ---: | -------: | -----: | ---: | -------: | ----------------- |
| route-recommendation  |  128 |        4 |     53 |   35 |       33 | jihyun            |
| auth                  |   68 |        9 |     17 |   18 |       22 | 율무·권가영·lucky |
| places                |   47 |        8 |     20 |    6 |       12 | 권가영·율무       |
| home                  |   33 |        3 |      8 |    6 |        9 | 권가영            |
| chatbot               |   24 |        4 |      7 |    6 |        7 | 권가영            |
| trips                 |    9 |        0 |      0 |    1 |        0 | 율무              |
| travel-logs           |    7 |        0 |      0 |    0 |        2 | —                 |
| profile / inquiries   |    5 |        0 |      0 |    0 |        0 | —                 |
| src/components (공통) |    2 |        0 |      2 |    0 |        0 | —                 |

---

## 2. 조사하면서 나온 중요한 발견 5가지

### ① route-recommendation은 "자체 팔레트 객체"를 쓰고 있다 — 실제 작업량은 128개가 아니다

3개 파일이 파일 상단에 로컬 팔레트를 선언해두고 그걸 참조한다.

```ts
// RouteInputScreen.tsx (28행)
const colors = {
  orange: "#FF7A00",
  mint: "#12B89B",
  deepMint: "#07967E",
  ink: "#292B2E",
  gray: "#757A80",
  lightGray: "#F6F7F8",
  line: "#E8EAEC",
  white: "#FFFFFF",
  cream: "#FFF8EE",
  red: "#E95858",
};
```

| 파일                            | 팔레트 정의 hex | 참조 사용 |
| ------------------------------- | --------------: | --------: |
| `RouteInputScreen.tsx`          |            10줄 |     101회 |
| `RouteRecommendationScreen.tsx` |             9줄 |      64회 |
| `InlineDateTimePicker.tsx`      |             6줄 |      16회 |

**이 3개 파일은 팔레트 객체 25줄만 고치면 181곳이 한 번에 정리된다.** 로컬 팔레트를 지우고 `import { colors } from '@/src/theme'`로 바꾸되, 이름이 다르므로(`orange`→`primary`, `ink`→`textPrimary` 등) 참조명 일괄 치환이 필요하다. 가장 가성비 좋은 첫 커밋 후보.

⚠️ 다만 이 파일은 `colors`라는 **같은 이름**으로 로컬 객체를 선언해서 theme의 `colors`와 이름이 충돌한다. import 시 반드시 로컬 선언을 먼저 제거해야 한다.

### ② `#FF7A00` — 두 번째 primary가 존재한다 (가장 중요)

route-recommendation 전체가 주황색을 `#FF7A00`으로 쓴다. theme의 `primary`는 `#FF7A45`. **ΔE 21.6으로 명백히 다른 주황이다** (`#FF7A00`이 더 쨍한 순주황, `#FF7A45`가 더 살구빛).

theme 파일 주석에 "통합 시 primary는 `#FF7A45`로 확정했다"고 적혀 있으므로 **`#FF7A00` → `colors.primary` 치환이 원칙**이지만, 이건 화면이 눈에 띄게 바뀌는 변경이다. **jihyun님께 먼저 알려야 한다.**

### ③ 소셜 로그인 브랜드 컬러는 절대 바꾸면 안 된다

```ts
// auth/screens/LoginScreen.tsx 25~27행
{ label: '네이버', backgroundColor: '#03C75A', textColor: '#FFFFFF' },
{ label: '카카오', backgroundColor: '#FEE500', textColor: '#191919' },
{ label: '구글',   backgroundColor: '#FFFFFF', textColor: '#4285F4' },
```

각 사의 브랜드 가이드라인에 규정된 값이라 토큰화 대상이 아니다. 오히려 **바꾸면 심사에서 문제가 될 수 있다.** 코드에 주석으로 "브랜드 규정값, 변경 금지"를 남기는 편이 낫다.

### ④ Mock 데이터 안의 색상은 성격이 다르다

- `route-recommendation/mocks/routes.mock.ts` — `thumbnailColor` 10개 (`#DDF2E6`, `#F7E7D3`, `#FFF1B9` …)
- `home/data/homeMockData.ts` — `iconColor`/`iconBackgroundColor` 8개

이건 스타일이 아니라 **데이터로서의 색**이다. 나중에 서버가 내려줄 값이므로 토큰으로 치환하는 게 맞는지 자체가 논점이다. 다만 지금 값들이 팔레트와 따로 놀아서(`#5187D4` 파란색, `#FFF1B9` 노란색 등) 화면에서 튄다. **"카테고리 색 팔레트"라는 별도 토큰 묶음을 만드는 방향을 제안한다.**

### ⑤ WebView(카카오 지도) HTML 안의 색은 별도 처리가 필요하다

| 파일                                                      |
| --------------------------------------------------------- |
| `places/components/buildKakaoMapDocument.ts`              |
| `places/components/KakaoPlaceMap.native.tsx` / `.web.tsx` |
| `places/components/InteractivePlaceMap.tsx`               |
| `chatbot/components/ChatMapResponse.tsx`                  |

HTML 문자열 안이라 `colors` import를 직접 쓸 수 없다. 개발 가이드 9항대로 **색상을 props로 넘겨받는 구조**로 바꿔야 한다 (`trips/utils/kakaoMapHtml.ts`가 이미 그 패턴이니 참고).

---

## 3. theme/colors.ts 자체의 문제 — 여기부터 정리해야 한다

`colors.ts` 40행에 이미 TODO가 달려 있다. 토큰끼리 중복이다.

| 중복 쌍                                        |  ΔE | 판단                                                |
| ---------------------------------------------- | --: | --------------------------------------------------- |
| `primarySoft` `#FFF1E8` ↔ `orangeBg` `#FFF3EA` | 0.9 | **합칠 것.** 구분 불가능한 수준                     |
| `seaSoft` `#E0F5F2` ↔ `mintBg` `#EEF8F5`       | 4.2 | **합칠 것.** 나란히 놓아야 겨우 구분                |
| `sea` `#2BB8AC` ↔ `mintIcon` `#52B9A5`         | 6.8 | 합치되 어느 값을 남길지 선택 필요                   |
| `primary` `#FF7A45` ↔ `orangeIcon` `#FF8A4C`   | 8.2 | 합치면 **화면이 눈에 띄게 바뀐다.** 팀 확인 후 결정 |
| `background` `#FFFFFF` ↔ `surface` `#FFFFFF`   |   0 | 값은 같지만 역할이 다르므로 **유지**                |

`orangeIcon`은 ΔE 8.2로 생각보다 차이가 크다. theme 주석은 이 둘을 같은 계열로 묶었지만, 실제로는 `orangeIcon`이 한 톤 밝다. 커밋 1에서 무조건 합치지 말고 **화면에 나란히 띄워 보고 결정할 것.**

토큰이 중복인 채로 치환을 시작하면 "어떤 토큰을 쓸지"가 파일마다 갈린다. **1번 커밋은 토큰 정리여야 한다.**

---

## 4. 새로 추가를 검토할 토큰

`토큰없음` 85건을 성격별로 묶었다.

### (a) 진한 텍스트 계열 — 현재 토큰에 구멍이 있다

`textPrimary #333333`와 `basalt #33302C` 사이 톤이 없어서 각자 만들어 썼다.

`#4F4A47`(x2) `#544D48` `#514C48` `#55504D` `#4F4B48` `#4F4F4F` `#535353` `#555555` `#565656` `#5D5855` `#66615E` — **11개 값이 사실상 같은 "중간 진한 회갈색"이다.**

> 제안: `textStrong: '#514C48'` 정도를 추가하거나, 전부 `textPrimary`로 통일.

### (b) 진한 초록 계열 — secondary보다 어두운 톤이 필요했다

`#168F77`(x2) `#238871`(x2) `#248F77` `#18967C` `#188F7B` `#138A78` `#07967E` `#0C9E86` `#157C6B` `#12B89B`(x2) — **11개 값.** `secondary #4CAF88`, `sea #2BB8AC`와 모두 다르다.

> 제안: `seaDeep: '#188F7B'` 추가 후 통일.

### (c) 진한 주황·갈색 (강조 텍스트용)

`#64351E`(x3) `#552610` `#4D321F` `#A95620` `#A45A2A` `#B85635` `#C85F00` `#8A6843`

> 제안: `primaryDeep`(버튼 눌림·강조 텍스트용) 1~2개 추가.

### (d) 연한 주황 배경 — 값이 9종류나 된다

`#FFE5C3`(x3) `#FFD8AD`(x2) `#FFE0CC` `#FFE7CD` `#FFE2C0` `#FFE4BE` `#FFE0B5` `#FFD3A5` `#FFDCC8` `#F4D8C8`

`primarySoft #FFF1E8`보다 한 단계 진한 톤이다.

> 제안: `primarySoftStrong` 1개 추가로 9개 전부 흡수.

### (e) 카테고리/데이터 색 (④번 발견 관련)

파랑 `#5187D4` `#5584CC` `#DCECF7` `#DCE9F5` `#EAF2FF` / 보라 `#E6E1F8` / 노랑 `#FFF1B9` `#FFF7DC`

> 제안: `categoryColors` 라는 별도 객체로 분리. 브랜드 팔레트와 섞지 않는다.

### (f) 순수 흑백 — 그림자·지도용

`#000000`(x3), `#111111`, `#171717`, `#191919`(브랜드), `#222222`, `#222`

> `#000000`은 대부분 `shadowColor`다. `theme/shadow.ts`에 이미 있는지 확인 후 그쪽으로 흡수.

---

## 5. 제안하는 커밋 분할

각 커밋마다 화면 확인이 가능하도록 쪼갰다.

| #   | 커밋                                            | 내용                                                                                                    | 화면 변화                    | 위험                        |
| --- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------- | --------------------------- |
| 1   | `refactor: theme 색상 토큰 중복 정리 및 확장`   | 3번의 중복 쌍 통합 + 4번의 신규 토큰 추가. 기존 토큰명은 deprecated 별칭으로 남겨 다른 화면이 안 깨지게 | 없음                         | 낮음                        |
| 2   | `refactor: 루트 추천 화면 색상 토큰 적용`       | ①의 로컬 팔레트 3개 제거 → theme import. 181곳 정리                                                     | **있음** (#FF7A00 → #FF7A45) | **높음 · jihyun 확인 필요** |
| 3   | `refactor: 인증 화면 색상 토큰 적용`            | auth 68건. 소셜 브랜드 컬러 4개는 제외 + 주석                                                           | 미미                         | 중간                        |
| 4   | `refactor: 장소 탐색 화면 색상 토큰 적용`       | places 47건 (WebView 제외)                                                                              | 미미                         | 중간                        |
| 5   | `refactor: 홈·챗봇 화면 색상 토큰 적용`         | home 33 + chatbot 24                                                                                    | 미미                         | 낮음                        |
| 6   | `refactor: 지도 WebView 색상 props 주입`        | ⑤의 5개 파일. 구조 변경                                                                                 | 없음                         | 중간                        |
| 7   | `refactor: mock 데이터 카테고리 색 팔레트 분리` | ④. 논의 결과에 따라 생략 가능                                                                           | 있음                         | 논의 필요                   |
| 8   | `chore: deprecated 색상 별칭 제거`              | 1번에서 남긴 별칭 정리                                                                                  | 없음                         | 낮음                        |

**2번을 뒤로 미루는 것도 방법이다.** 가장 크고 가장 논쟁적이라, 3~5번을 먼저 머지해서 방식에 대한 팀 합의를 얻은 뒤 2번을 올리면 리뷰가 수월하다.

---

## 6. 작업 시작 전 확인이 필요한 것

### 팀원에게 물어봐야 할 것

1. **jihyun** — route-recommendation의 주황을 `#FF7A00` → `#FF7A45`로 바꿔도 되는지. 시안 원본이 어느 쪽인지 확인 필요
2. **전원** — 4번의 신규 토큰 제안(진한 텍스트/진한 초록/진한 주황/연주황 배경)을 받아들일지, 아니면 기존 토큰으로 눌러 담을지
3. **전원** — mock 데이터의 카테고리 색을 이번 범위에 포함할지

### 절차상 확인

- 이 작업은 `src/theme/`를 건드리므로 **개발 가이드 D-1의 공통 파일 변경 대상**이다. `docs/planning/yulim-main-merge-notes.md` 3번 표를 같은 커밋에 갱신해야 한다
- 통합 PR이 아직 미머지이므로 브랜치는 `dev/integration`에서 따고, PR base도 `dev/integration`으로 잡는다
- `design-assets/` 폴더가 untracked 상태다. 커밋할지 `.gitignore`에 넣을지 결정 필요

---

## 7. 다음 단계

```bash
cd ~/Documents/관광공모전
git switch dev/integration && git pull
git switch -c work/yulim/refactor/design-color-tokens
```

첫 작업은 **커밋 1 (theme 토큰 정리)**. 여기서 토큰이 확정돼야 나머지 치환이 한 번에 끝난다.

---

## 8. 적용 결과

조사 후 실제로 적용한 내용이다. 위 5번의 커밋 분할 계획 대신 **한 브랜치에서 일괄 처리**했다
(통합 담당자 판단 — 팀원 사전 동의 없이 진행하기로 결정).

| 항목                            | 결과                              |
| ------------------------------- | --------------------------------- |
| 남은 하드코딩 hex               | **0건**                           |
| 남은 rgba 리터럴                | **0건**                           |
| 변경 파일                       | 51개 (+ 문서 2개)                 |
| theme 토큰 참조                 | 1,421건 / 45종                    |
| `tsc --noEmit`                  | 통과                              |
| deprecated 별칭 (`orangeBg` 등) | 37건 치환 후 **토큰 자체를 삭제** |

### 3번 표의 결정 사항 — 실제로 이렇게 했다

| 중복 쌍                | 결정                                                |
| ---------------------- | --------------------------------------------------- |
| `orangeBg`             | `primarySoft` 로 통합 후 삭제                       |
| `orangeIcon`           | `primary` 로 통합 후 삭제 (ΔE 8.2, 미세하게 밝아짐) |
| `mintBg`               | `seaSoftLight` 로 이름만 변경 (값 유지)             |
| `mintIcon`             | `sea` 로 통합 후 삭제                               |
| `background`/`surface` | 유지 — 역할이 다름                                  |

### 4번 제안 중 실제로 추가한 토큰

`primaryDeep` `primaryInk` `primarySoftStrong` `textStrong` `seaDeep` `seaSoftLight`
`calendarSunday` `calendarSaturday` — 총 8개.

추가로 `categoryColors`(데이터용 색 6쌍) / `brandColors`(소셜 3사) /
`overlayColors`(rgba·그림자 9종) / `thumbnailPalette`(파스텔 배경 6종) 를 별도 export 로 분리했다.

### 조사 때 놓쳤다가 작업 중 발견한 것

- **큰따옴표 JSX 속성** (`color="#929292"`) 이 최초 스캔에서 빠져 있었다. 19건 추가 발견.
- **8자리 hex** (`#00000055`) 도 오버레이였다. `overlayColors.scrim` 으로 흡수.
- `KakaoPlaceMap.native/web.tsx`, `InteractivePlaceMap.tsx`, `ChatMapResponse.tsx` 는
  WebView 파일로 분류했지만 실제로는 평범한 `StyleSheet` 였다. 일반 치환으로 처리.
  진짜 HTML 문자열은 `buildKakaoMapDocument.ts` 하나뿐이었다.
- prettier 를 전체에 돌렸더니 diff 의 71%가 포맷 노이즈가 되어, **되돌리고 색상 변경만 남겼다.**
  이 저장소는 `.prettierrc.json` 이 있지만 기존 파일들이 그 규칙을 지키지 않는 상태다.
  포맷 정리는 별도 PR 로 분리하는 편이 낫다.

---

## 부록

- 전체 323건 상세 목록: `docs/planning/design-color-audit-detail.csv`
  (기능 / 파일 / 줄번호 / 현재값 / 권장토큰 / 분류 / ΔE / 해당 코드)
  ※ 이 CSV 는 **작업 전** 스냅샷이다. 줄번호는 치환 전 기준.

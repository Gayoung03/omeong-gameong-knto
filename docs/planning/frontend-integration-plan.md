# 프론트엔드 통합 작업 순서

작성일: 2026-08-09 / 담당: 율림 (단독 진행)
기준: `origin/main` = df35ea6 / 각 `origin/dev/*-main` 최신
※ 시작 전 `git fetch --all` 로 아래 수치 재확인할 것 (본 문서는 마지막 fetch 기준)

---

## 전체 그림

```
[0] 준비          fetch · 결정 3개 확정 · dev/integration 생성
      ↓
[1] 지현 머지      충돌 0   ← 무위험 구간
[2] 율림 머지      충돌 0   ← 무위험 구간
[3] 가영 머지      충돌 1   ← _layout.tsx + 라우트/인증/env 3건 처리
[4] 행운 머지      충돌 7   ← theme·config·package
      ↓
[5] 통합 검증 → PR  dev/integration → main (PR 1개)
      ↓
[6] 토큰 확정      코드 안 건드림. 매핑표만 만든다  ← "한 번에" 하는 부분
      ↓
[7] 디자인 적용     features 폴더별 PR 분할 · 4명 병렬  ← "나눠서" 하는 부분
```

**원칙: [1]~[5]는 "빌드되고 돌아가는 것"까지만. 디자인 판단은 전부 [6]으로 미룬다.**

---

## 왜 이 순서인가 (실측 근거)

### 머지 순서 — 3가지 순서를 실제로 돌려본 결과

| 순서 | 지현 | 율림 | 가영 | 행운 | 합계 |
| --- | --- | --- | --- | --- | --- |
| **지현→율림→가영→행운 (채택)** | **0** | **0** | 1 | 7 | 8 |
| 가영→지현→율림→행운 | 0 | 1 | 0 | 7 | 8 |
| 행운→율림→가영→지현 | 0 | 7 | 1 | 0 | 8 |

총 충돌 수는 어느 순서든 8건으로 같다. 순서가 총량을 줄이지는 않는다.
**채택 이유는 리스크 배치다.**

- 앞의 두 번이 충돌 0 → 전체 작업량의 절반(106파일, 15,000줄)을 무위험으로 끝낸다
- 그 시점에 앱이 돌아가므로, 뒤에서 깨졌을 때 **"원래 되던 건지"를 판별할 기준선**이 생긴다
- 행운은 어느 순서에 놓든 항상 7건을 몰고 온다 → 마지막이 맞다
- 지현은 **누구와도 겹치지 않는다** (율림 0 / 가영 0 / 행운 0)

### 겹치는 파일 (쌍별 실측)

|  | 지현 | 율림 | 가영 | 행운 |
| --- | --- | --- | --- | --- |
| **지현** | — | 0 | 0 | 0 |
| **율림** | 0 | — | 4 | 8 |
| **가영** | 0 | 4 | — | 3 |
| **행운** | 0 | 8 | 3 | — |

겹침은 전부 공통 파일 9개(`theme/` 4개, `app/_layout.tsx`, `package.json`+lock, `app.config.ts`, `.env.example`)에만 몰려 있다. `src/features/` 안의 기능 코드끼리는 충돌이 0이다.

### 통합 먼저 → 디자인 나중이 맞는 이유

통합이 끝나면 `src/features/` 소유권이 사람별로 갈린다.

```
율림  → trips
지현  → route-recommendation
가영  → auth* chatbot home places
행운  → auth* inquiries notices profile settings travel-logs
```
`auth`만 둘이 겹치지만 **파일 단위로는 안 겹친다** (가영=로그인·회원가입 / 행운=로그아웃·탈퇴).

→ **통합 후에는 디자인 정리를 4명이 병렬로 돌려도 충돌이 0이다.**
   순서를 반대로 하면 각자 브랜치에서 `theme/` 을 건드려야 하고, 그건 지금
   행운이 율림 토큰을 지워버린 상황의 재발이다.
   게다가 디자인 통일은 화면을 다 모아놓고 나란히 봐야 판단이 되는 일이다.

---

## [0] 준비

### 0-1. 시작 전 확정할 것 3개

| # | 항목 | 권장 |
| --- | --- | --- |
| ① | **primary 색상** — 현재 4가지(`#FF7A45` 율림 / `#FF8A3D` 행운 / `#FF7A00` 지현 / 가영 배경계열) | 시안 원본 값. 없으면 율림 `#FF7A45` (theme 토큰으로 가장 널리 사용 중) |
| ② | **카카오 키 변수명** — `EXPO_PUBLIC_KAKAO_JS_KEY`(율림) vs `EXPO_PUBLIC_KAKAO_JAVASCRIPT_KEY`(가영) | `EXPO_PUBLIC_KAKAO_JS_KEY` |
| ③ | **`web.output`** — `'single'`(율림) vs `'static'`(행운) | **`'single'`**. `'static'` 이면 webview·view-shot 이 Node 프리렌더에서 깨져 웹 빌드 실패 |

나머지 디자인 결정은 전부 [6]으로 미룬다.

### 0-2. 브랜치 생성
```bash
cd ~/Documents/관광공모전
git fetch --all
git switch -c dev/integration origin/main
```
> 통합 브랜치를 따로 두는 이유: 꼬여도 `main` 은 무사하고, 브랜치를 지우고 다시 시작할 수 있다.

> 현재 로컬은 `work/yulim/docs/git-convention` 에 있고 `design-assets/`, 이 문서가 untracked 상태다.
> 통합 시작 전에 정리하거나 stash 할 것.

---

## ⚠️ 매 머지 후 검증 순서 (반드시 이 순서로)

```
merge → expo start (타입 재생성 + 화면 확인) → Ctrl+C → tsc → lint → push
```

**`tsc` 를 먼저 돌리면 없는 에러가 뜬다.** Expo Router 는 `app/` 폴더를 스캔해
`.expo/types/router.d.ts` 에 라우트 타입을 자동 생성하는데, 이 파일은 **`expo start` 실행 시에만 갱신**된다.
git merge 로 라우트 파일이 추가된 것은 반영되지 않으므로, 머지 직후 `tsc` 를 돌리면
새로 들어온 라우트가 `is not assignable to type` 에러로 잡힌다.

```bash
rm -rf apps/mobile/.expo/types    # 낡은 타입 제거
npx expo start                    # 재생성 + 화면 확인 → Ctrl+C
npx tsc --noEmit
```

---

## [1] 지현 머지 — 충돌 0 ✅ 완료 (2026-08-09)

```bash
git merge --no-ff origin/dev/jihyun-main -m "merge: 루트 추천 화면 통합"
```
- 충돌 0. 프론트 10개 파일만 들어옴 (2,517줄)
- **DB 스키마·마이그레이션은 PR #19 로 main 에 먼저 들어와 있었고 내용이 동일**해서 diff 에 안 나타남
- `npm install` 불필요 — 지현 코드가 쓰는 패키지가 전부 main 에 이미 있음
- `.expo/types` 문제로 `tsc` 가 한 번 실패 → 재생성 후 통과
- 결과: `tsc` ✅ / `lint` ✅

---

## [2] 율림 머지 — 충돌 0 ✅ 완료 (2026-08-09)

커밋 `16f339a`. 충돌 0. `tsc` ✅ / `lint` ✅ / 5개 탭 정상.

**통과 판정 기준: 빨간 크래시 화면이 뜨는가.** 콘솔 경고는 통과로 친다.
이 단계에서 확인된 웹 콘솔 경고 2종은 모두 **머지 때문이 아니라 원래 있던 것**이며 [7]로 넘긴다.

| 경고 | 원인 | 범위 | 처리 |
| --- | --- | --- | --- |
| `<button>` 중첩 (Pressable 안의 Pressable) | RN Web 이 `accessibilityRole="button"` 을 DOM `<button>` 으로 렌더링. 네이티브에선 정상 패턴 | 율림 7 + 지현 3 파일 | [7] 각 담당자 |
| `"shadow*" style props are deprecated` | `shadowColor`/`shadowOffset` 직접 사용 | 율림 5 + 지현 2 파일 | [7] 행운 `shadow.ts`(`Platform.select` + `boxShadow`) 채택으로 일괄 해결 |

### 원래 명령어

```bash
git merge --no-ff origin/dev/yulim-main -m "merge: 내 여행 화면 통합"
cd apps/mobile && npm install     # 패키지 8개 추가되므로 필요
rm -rf .expo/types && npx expo start
# Ctrl+C 후
npx tsc --noEmit && npm run lint
```
확인: 내 여행 탭 + 루트 탭 둘 다 정상 동작

**여기까지가 무위험 구간. 하루 안에 끝난다. 반드시 push 해두고 한숨 돌릴 것.**

---

## [3] 가영 머지 — 충돌 1건

```bash
git merge --no-ff origin/dev/gayoung-main -m "merge: 인증·홈·장소탐색 통합"
```

### 충돌: `app/_layout.tsx`
바깥 `GestureHandlerRootView` 래퍼는 **반드시 살리고**(율림 드래그 제스처용),
안쪽 `Stack.Screen` 목록만 양쪽 합집합으로.

### 충돌은 안 나지만 반드시 함께 처리할 것 3가지

1. **`(tabs)/index.tsx` 삭제 + `(tabs)/(home)/` 그룹 추가**가 제대로 반영됐는지 확인.
   둘 다 남아 있으면 `/` 라우트가 중복돼 Expo Router 가 에러를 낸다.
   `(tabs)/_layout.tsx` 의 `tabIcons` 키도 `index` → `(home)` 이어야 한다 (가영 버전이 이미 그렇다).
2. **인증 게이트 우회.** 가영의 `(tabs)/_layout.tsx` 는 세션이 없으면 `/login` 으로 강제 이동시킨다.
   통합 QA 중 모든 탭이 막히므로 임시 우회를 넣는다. → [5]에서 원복.
   ```tsx
   if (!session && !__DEV__) { router.replace('/login'); return; }
   ```
3. **카카오 키 변수명 통일** (결정 ②). 가영 쪽 2개 파일 수정:
   `features/places/components/InteractivePlaceMap.tsx`, `features/chatbot/components/ChatMapResponse.tsx`
   → `.env.example`, `apps/mobile/.env.example`, `apps/mobile/.env` 도 함께

---

## [4] 행운 머지 — 충돌 7건 (여기가 진짜 작업)

```bash
git merge --no-ff origin/dev/lucky-main -m "merge: 마이페이지·여행기록·공통 UI 통합"
```

### ⚠️ 이 단계의 유일한 규칙: **합집합. 아무것도 지우지 않는다.**
행운은 율림의 확장 토큰(`primarySoft`, `leaf`, `sea`, `basalt`, `textTertiary`, `radius.full`,
`typography` 확장 스케일)을 **삭제한 상태**다. 그대로 행운 것을 채택하면 율림 화면이 컴파일조차 안 된다.
반대로 율림 것만 쓰면 행운 화면이 깨진다.
중복 토큰(`primarySoft`↔`orangeBg`, `seaSoft`↔`mintBg`)이 남는 게 **정상이자 의도된 임시 상태**다.
보기 싫어도 여기서 정리하지 말 것 — 정리하는 순간 디자인 판단이 통합 안으로 새어 들어온다. → [6]에서 걷어낸다.

| 충돌 파일 | 해결 |
| --- | --- |
| `src/theme/colors.ts` | 합집합 (아래 코드) |
| `src/theme/typography.ts` | 합집합. 율림 확장 스케일 유지 + `title` 크기만 택일(24 vs 21) |
| `src/theme/radius.ts` | 율림 것 (`full: 999` 필요) |
| `src/theme/index.ts` | 합집합 — `export * from './shadow'` 추가 (행운 `shadow.ts` 가져오기) |
| `app.config.ts` | plugins 합집합 + `web.output: 'single'` (결정 ③) |
| `package.json` | 합집합 — 버전 충돌 없음 |
| `package-lock.json` | 손대지 말고 재생성 |

```ts
// src/theme/colors.ts — 통합본
export const colors = {
  primary: '#FF7A45',        // ← 결정 ①
  secondary: '#4CAF88',
  background: '#FFFFFF',
  surface: '#FFFFFF',
  textPrimary: '#333333',
  textSecondary: '#7A7A7A',
  textTertiary: '#A8A49B',
  border: '#EEEEEA',
  divider: '#E5E5E5',
  success: '#2EAF6D',
  warning: '#F5A623',
  error: '#E5484D',
  errorBg: '#FDECEC',
  // 시안 키 컬러 (율림)
  primarySoft: '#FFF1E8',
  leaf: '#4E7A3A', leafSoft: '#EAF3E2',
  sea: '#2BB8AC',  seaSoft: '#E0F5F2',
  basalt: '#33302C', basaltSoft: '#F1EFEA',
  // 역할 토큰 (행운)
  mintBg: '#EEF8F5', mintIcon: '#52B9A5',
  orangeBg: '#FFF3EA', orangeIcon: '#FF8A4C',
  iconGray: '#7E8582', neutralGray: '#F5F6F4',
} as const;
```

```bash
# package-lock 은 충돌 해결하지 말고 재생성
git checkout --ours apps/mobile/package-lock.json
cd apps/mobile && npm install
git add package-lock.json
```

**`app.config.ts` plugins 합집합**: `expo-router`, `expo-secure-store`,
`@react-native-community/datetimepicker`, `expo-sharing`, `expo-media-library`(율림 권한문구),
`expo-image-picker`(행운 권한문구)

**`package.json` 추가분** (버전 충돌 없음):

| 사람 | 패키지 |
| --- | --- |
| 율림 | `@react-native-community/datetimepicker` 9.1.0, `react-native-draggable-flatlist` ^4.0.3, `react-native-reanimated` 4.5.1, `expo-clipboard`, `expo-sharing`, `expo-media-library`, `react-native-view-shot` 5.1.0, `react-native-webview` 13.16.1 |
| 행운 | `@gorhom/bottom-sheet` ^5.2.14, `expo-image-picker` ~57.0.7, `react-native-calendars` ^1.1314.0, `react-native-reanimated` 4.5.1, `react-native-worklets` 0.10.1 |
| 가영 | (신규 없음) |

`@gorhom/bottom-sheet` 때문에 `app/_layout.tsx` 에 `BottomSheetModalProvider` 래퍼도 필요하다.
최종 루트 레이아웃:
```tsx
<GestureHandlerRootView style={{ flex: 1 }}>   {/* 율림·행운 */}
  <QueryClientProvider client={queryClient}>
    <BottomSheetModalProvider>                 {/* 행운 */}
      <Stack screenOptions={{ headerShown: false }}>
        {/* 4명 Stack.Screen 전부 합집합 */}
      </Stack>
    </BottomSheetModalProvider>
  </QueryClientProvider>
</GestureHandlerRootView>
```

---

## [5] 통합 검증 → PR

### 체크리스트
- [ ] `npx tsc --noEmit` 통과
- [ ] `npm run lint` 통과 (율림이 직접 실행)
- [ ] `npx expo start` → 5개 탭 전부 진입 (홈·루트·챗봇·내 여행·마이)
- [ ] 각 탭에서 하위 화면 최소 1개씩 진입
- [ ] `app/routes/result.tsx` **어느 `_layout` 에도 미등록** → `Stack.Screen` 추가했는지 확인
- [ ] 지현 `RouteBottomNavigation` 이 `(tabs)` 탭바와 이중으로 뜨지 않는지
- [ ] 인증 게이트 `__DEV__` 우회 **원복**
- [ ] 카카오 지도 2곳(내 여행 지도탭 / 장소탐색) 모두 렌더링

### PR
```
dev/integration → main   (PR 1개)
```
diff 가 300파일이 넘어 통째 리뷰는 불가능하다. PR 본문에 머지 커밋 4개를 나열하고
**"충돌 해결이 있었던 파일 9개"만 집중 리뷰** 요청한다.
각 담당자에게는 "본인 화면이 통합 후에도 정상 동작하는지"만 확인받는다.

PR 본문에는 `docs/planning/yulim-main-merge-notes.md` 의 누적 공유 항목도 함께 옮긴다.

---

## [6] 토큰 확정 — 코드는 건드리지 않는다

**여기가 "한 번에" 해야 하는 부분.** 반나절이면 끝난다.

전체 코드에 **고유 색상값이 234개**, 하드코딩이 308건 있다.
이걸 PR 하나에 담으면 리뷰도 bisect 도 불가능하므로 **결정은 한 번에, 적용은 나눠서** 간다.

### 순서
1. 통합된 앱의 **모든 화면을 캡처해서 나란히 놓는다** (이제서야 판단 근거가 생긴다)
2. **공통 UI 컴포넌트 정본부터 결정** ← 색상 매핑보다 먼저
   행운이 만든 `src/components/ui/` 10개(Button, Card, Chip, IconButton, ListItem,
   ScreenHeader, SectionHeader, StatTile, Avatar, RemoteImage)를 정본으로 채택할지.
   **채택하면 색상을 하나씩 바꾸는 대신 컴포넌트를 통째로 교체하는 방식이 되어 작업량이 절반 이하로 준다.**
3. 최종 토큰 세트 확정 + [4]에서 남긴 중복 토큰 정리 대상 확정
4. **`234개 색상 → 토큰` 매핑표** 작성 → `docs/planning/design-token-map.md`

산출물은 문서 하나. 이게 있어야 [7]을 남에게 넘길 수 있다.

### [6]에서 정해야 할 것 — 화면 폭 처리 (통합 중 발견)

지현 화면만 웹에서 폰 크기로 보이고 나머지는 화면 전체로 늘어난다.
원인은 지현이 `maxWidth: 430` 짜리 `mobileFrame` 스타일을 직접 넣었기 때문
(`RouteInputScreen.tsx:1016`, `RouteRecommendationScreen.tsx:579-583`. 지현 파일 2개에만 존재).

**율림·행운·가영 쪽이 RN 기본 동작이고 지현이 예외다.** 실기기·시뮬레이터에서는 뷰포트가
폰 너비라 둘 다 똑같이 보이므로, **웹 미리보기에서만 나타나는 차이**다.

→ 통합 중에는 건드리지 않는다. [6]에서 둘 중 하나로 결정:
- **(a) 지현의 `maxWidth` 제거** — 제출물이 모바일 앱이면 이쪽이 정석
- **(b) 공통 `MobileFrame` 래퍼를 만들어 전 화면에 적용** — 웹으로 시연·심사한다면 이쪽

### 지현 코드 특이사항 (통합 중 발견)

`RouteInputScreen.tsx:28` 에서 **`const colors = {...}` 를 로컬로 선언해 theme 을 통째로 가리고 있다.**
(`colors.white` 처럼 theme 에 없는 키를 쓰는데도 타입 에러가 안 나는 이유)
→ [7]에서 지현 파일은 단순 색상 치환이 아니라 **로컬 palette 삭제 + 토큰 매핑**이 필요하다.

### 하드코딩 현황 (작업량 배분 근거)

| 담당 | tsx 파일 | theme import한 파일 | 하드코딩 색상 |
| --- | --- | --- | --- |
| 율림 | 56 | 42 | 19건 |
| 행운 | 107 | 76 | 21건 |
| 가영 | 40 | 18 | **173건** |
| 지현 | 19 | 2 | **135건** |

---

## [7] 디자인 적용 — features 폴더별 분할 · 병렬

폴더가 사람별로 갈리므로 **4명이 동시에 작업해도 충돌이 0이다.**

| PR | 범위 | 적임자 |
| --- | --- | --- |
| A | `features/trips` | 율림 |
| B | `features/route-recommendation` | 지현 (135건) |
| C | `features/home` `places` `chatbot` `auth`(로그인·회원가입) | 가영 (173건) |
| D | `features/profile` `travel-logs` `inquiries` `notices` `settings` | 행운 |
| E | `src/theme` 중복 토큰 제거 | 율림 (A~D 머지 후 마지막) |

우선순위(시간이 부족하면 위에서부터):
1. **키 컬러** — 지현 `#FF7A00`, 행운 `#FF8A3D` → 정본 `primary` (전체 톤이 제일 크게 잡힌다)
2. **상단 헤더** — 화면마다 제각각 → `ScreenHeader` 로 통일
3. **카드·버튼** — `src/components/ui/` 로 교체
4. 나머지 색상·폰트크기·라운드

---

## 통합 후 남는 정리 과제 (별도 PR)

- **카카오 지도 구현 2벌** — 율림 `features/trips/utils/kakaoMapHtml.ts` +
  가영 `features/places/components/buildKakaoMapDocument.ts` → 공통으로 승격
- **바텀시트 2벌** — 율림 RN `Modal` vs 행운 `@gorhom/bottom-sheet`
  → `@gorhom/bottom-sheet` 로 통일 (Provider 가 이미 루트에 들어간다)
- **DateTimePicker 2벌** — 율림 `@react-native-community/datetimepicker` vs 지현 자체구현 `InlineDateTimePicker`
- 일정 추가 화면(목업 10) — trips ↔ places 검색 재사용 협의

---

## 절대 하지 말 것

- `main` 에 직접 push
- 4개를 한 번에 옥토퍼스 머지
- `package-lock.json` 손으로 충돌 해결 (→ 재생성)
- **[4]에서 theme 토큰을 지우거나 정리하기** (→ [6]으로)
- 통합 PR 안에서 디자인 리팩터링까지 같이 하기
- **[5]~[6] 사이에 새 기능 작업 재개** — 하드코딩이 또 늘어 매핑표가 낡는다.
  일정상 계속 가야 한다면 최소한 **"통합 이후 새 코드는 토큰만"** 규칙을 팀에 못 박을 것

---

## 변경 이력
- 2026-08-09 최초 작성
- 2026-08-09 단독 진행 전제로 수정. 머지 순서 실측 검증, "기반 PR 선행" 철회
- 2026-08-09 최종 작업 순서로 재정리. [6] 토큰 확정 단계 신설, [7] 병렬 분할안 추가

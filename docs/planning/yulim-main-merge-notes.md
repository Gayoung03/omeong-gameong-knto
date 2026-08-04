# 내 여행(trips) — main 머지 전 공유 사항

율무 담당 "내 여행" 화면 작업에서 **팀원에게 공유해야 하는 항목**을 누적 기록하는 문서.
개인 통합 브랜치(`dev/yulim-main`)에서 작업하는 동안에는 팀에 영향이 없지만,
`main`에 합칠 때는 아래 내용을 팀원이 알아야 한다.

- **작성 규칙**: 라이브러리를 설치하거나 공통 파일을 건드릴 때마다 해당 표에 한 줄 추가한다.
- **사용처**: `main` PR 본문 작성 시 5번 항목을 그대로 옮긴다.

---

## 1. 설치한 라이브러리 (완료)

| 패키지                                   | 버전    | 설치 이유                                     | 반영 PR |
| ---------------------------------------- | ------- | --------------------------------------------- | ------- |
| `@react-native-community/datetimepicker` | 9.1.0   | 여행 정보 편집(목업 02)의 여행 기간 날짜 선택 | #5      |
| `react-native-draggable-flatlist`        | ^4.0.3  | 일정 편집(목업 09)의 드래그 순서 변경         | #8      |
| `react-native-reanimated`                | 4.5.1   | 위 라이브러리의 peer dependency               | #8      |
| `expo-clipboard`                         | ~57.0.1 | 공유 시트(목업 06)의 링크 복사                | #9      |
| `expo-sharing`                           | ~57.0.8 | 만든 일정 이미지를 다른 앱으로 공유           | #9      |
| `react-native-view-shot`                 | 5.1.0   | 일정 카드를 이미지로 캡처(목업 07)            | #9      |
| `expo-media-library`                     | ~57.0.3 | 캡처한 이미지를 사진첩에 저장                 | #9      |
| `react-native-webview`                   | 13.16.1 | 지도 탭(목업 03)에서 카카오 지도 JS API 사용  | 예정    |

> `datetimepicker`는 웹을 지원하지 않아 `DateRangeField.web.tsx`로 대체 구현을 분리했다.
> Metro가 플랫폼별로 자동 선택하므로 웹에서도 화면이 깨지지 않는다.

> `react-native-reanimated`는 원래 `expo-router`를 통해 4.5.3이 들어와 있었고,
> `npx expo install`이 SDK 57 호환 버전인 **4.5.1**로 맞춰 `package.json`에 고정했다.
> 새로 늘어난 패키지는 `react-native-draggable-flatlist` 하나뿐이다.

---

## 2. 설치 예정 라이브러리

| 패키지 | 예정 작업 | 상태 | 비고 |
| ------ | --------- | ---- | ---- |
| (없음) |           |      |      |

### 지도 연동 방식 — WebView vs 네이티브 SDK

초안 단계에서는 **WebView 방식**으로 진행한다. 최종 방식은 팀 결정이 필요하다.

**WebView (카카오 지도 JavaScript API)**

- 카카오가 공식 제공하는 JS API를 그대로 사용
- `react-native-webview` 하나만 설치하면 되고 **Expo Go에서 바로 확인 가능**
- **웹 배포로 전환해도 그대로 동작한다** (차선책이 "웹에서 앱처럼"이라면 이쪽이 유리)
- 단점: 마커가 많아지면 성능 저하, RN↔WebView 통신을 `postMessage`로 직접 배선해야 함,
  배포 시 카카오 개발자 콘솔의 플랫폼·도메인 등록 누락으로 지도가 안 뜨는 사례가 보고됨

**네이티브 SDK**

- 카카오가 **React Native 공식 바인딩을 제공하지 않는다.** 커뮤니티 패키지에 의존하거나
  네이티브 모듈 + Expo config plugin 을 직접 만들어야 함
- **개발 빌드가 필수** — 현재 프로젝트 경로의 한글 때문에 `expo run:ios` 가 실패한다 (PART B-6 참고)
- 성능과 제스처 처리는 우수

**팀에 확인이 필요한 것**

1. 스토어 배포와 웹 배포 중 어느 쪽을 기준으로 잡을지
2. 로그인 등 다른 화면에서 카카오 **네이티브 SDK** 를 쓸 계획이 있는지
   → 있다면 팀 전체가 개발 빌드로 넘어가야 하고, 한글 경로 문제부터 풀어야 한다

### 참고: `react-native-draggable-flatlist` 호환성 확인 결과 (설치 완료)

- 버전 **4.0.3** (2025-05-06 배포)
- peer 요구사항: `react-native >=0.64.0`, `react-native-gesture-handler >=2.0.0`, `react-native-reanimated >=2.8.0`
  → 현재 프로젝트(RN 0.86.2 / gesture-handler 2.32.0 / reanimated 4.5.1)에서 모두 충족
- Reanimated 4에서 제거된 `useAnimatedGestureHandler`를 사용하지 않고,
  Gesture Handler의 신 API(`Gesture.Pan()` + `GestureDetector`)를 사용 → Expo SDK 57 환경과 충돌 없음

---

## 3. 공통 파일 변경 내역

| 파일                                 | 변경 내용                                                                               | 반영 PR |
| ------------------------------------ | --------------------------------------------------------------------------------------- | ------- |
| `src/theme/colors.ts`                | 시안 키 컬러 확장 토큰 추가 (primarySoft, leaf, sea, basalt 등)                         | #3      |
| `src/theme/typography.ts`            | 촘촘한 화면용 확장 스케일 추가 (sectionTitle, subtitle, label, caption, micro)          | #3      |
| `src/theme/radius.ts`                | radius 토큰 신규 추가                                                                   | #3      |
| `src/theme/index.ts`                 | radius export 추가                                                                      | #3      |
| `src/theme/colors.ts`                | 앱 기본 배경색을 화이트(`#FFFFFF`)로 변경 — 팀 결정 사항                                | #6      |
| `app.config.ts`                      | `plugins` 배열에 `@react-native-community/datetimepicker` 추가                          | #5      |
| `app/_layout.tsx`                    | 최상단을 `GestureHandlerRootView`로 감싸기 (드래그 제스처 인식용)                       | #8      |
| `package.json` / `package-lock.json` | draggable-flatlist, reanimated 추가                                                     | #8      |
| `app.config.ts`                      | `plugins`에 `expo-sharing` 추가, `expo-media-library`를 사진 접근 권한 문구와 함께 추가 | #9      |
| `package.json` / `package-lock.json` | clipboard, sharing, view-shot, media-library 추가                                       | #9      |
| `apps/mobile/.gitignore`             | `/ios`, `/android` 추가 (expo prebuild 산출물 커밋 방지)                                | #9      |
| `apps/mobile/.env.example`           | 신규. `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_KAKAO_JS_KEY`                                 | 예정    |
| `.env.example`                       | Mobile 항목은 `apps/mobile/.env` 에 넣어야 한다는 안내 추가                             | 예정    |
| `package.json` / `package-lock.json` | react-native-webview 추가                                                               | 예정    |

> **`app/_layout.tsx`는 충돌 위험이 큰 파일이다.** 다른 팀원도 라우트를 추가하면서 건드리게 된다.
> 변경 내용 자체는 기존 트리를 `GestureHandlerRootView`로 한 겹 감싼 것뿐이라
> 충돌이 나면 바깥 래퍼만 살리고 안쪽 `Stack.Screen` 목록은 양쪽 것을 합치면 된다.

---

## 4. 팀원이 해야 할 일

`main` 머지 후 각자:

```bash
git pull
cd apps/mobile && npm ci
```

`npm install`이 아니라 **`npm ci`** 를 쓴다. `package-lock.json` 기준으로 정확히 같은 버전이 설치된다.

### `package-lock.json` 충돌이 났다면

여러 사람이 각자 다른 패키지를 설치한 뒤 한꺼번에 만나면 lock 파일이 충돌한다. 손으로 풀지 말 것.

```bash
git checkout --theirs apps/mobile/package-lock.json   # 또는 main 쪽 것을 채택
cd apps/mobile && npm install                          # package.json 기준으로 lock 재생성
git add package-lock.json
```

`package.json`(사람이 쓴 파일)만 정확히 병합하면 lock은 다시 만들면 된다.

---

## 5. main PR 본문에 옮길 내용

```markdown
## 신규 설치 라이브러리

- @react-native-community/datetimepicker@9.1.0 — 여행 기간 날짜 선택
  (웹 미지원이라 *.web.tsx 대체 구현 분리)
- react-native-draggable-flatlist@^4.0.3 — 일정 편집 화면의 드래그 순서 변경
- react-native-reanimated@4.5.1 — 위 라이브러리의 peer dependency
  (원래 expo-router를 통해 들어와 있던 것을 package.json에 명시적으로 고정)
- expo-clipboard@~57.0.1 — 공유 링크 복사
- expo-sharing@~57.0.8 — 만든 일정 이미지를 다른 앱으로 공유
- react-native-view-shot@5.1.0 — 일정 카드를 이미지로 캡처
- expo-media-library@~57.0.3 — 캡처한 이미지를 사진첩에 저장
- react-native-webview@13.16.1 — 지도 탭에서 카카오 지도 JavaScript API 사용

## 공통 파일 변경

- src/theme/ : colors·typography·radius 토큰 확장, 기본 배경색 화이트로 변경
- app/_layout.tsx : 최상단을 GestureHandlerRootView로 감쌈 (드래그 제스처 인식용)
- app.config.ts plugins :
  - @react-native-community/datetimepicker
  - expo-sharing
  - expo-media-library (사진 접근 / 사진첩 저장 권한 문구 포함)
- apps/mobile/.gitignore : /ios, /android 추가
  (expo prebuild 가 만드는 217MB 네이티브 폴더가 커밋되지 않도록)
- apps/mobile/.env.example 신규 추가 (EXPO_PUBLIC_API_URL, EXPO_PUBLIC_KAKAO_JS_KEY)
  Expo 는 expo start 를 실행하는 폴더에서 .env 를 읽으므로 모바일 환경변수는
  저장소 루트가 아니라 apps/mobile/.env 에 넣어야 합니다. 루트 .env.example 에도 안내를 넣었습니다.

## 팀원 확인 사항

- pull 후 `cd apps/mobile && npm ci` 실행 필요
- 네이티브 권한이 추가되어 시뮬레이터에서 처음 실행할 때 사진 접근 권한을 물어봅니다
- 지도 탭을 보려면 apps/mobile/.env 에 EXPO_PUBLIC_KAKAO_JS_KEY 가 필요합니다.
  카카오 개발자 콘솔 > 플랫폼 > Web 사이트 도메인에 https://localhost 등록도 함께 필요합니다.
  (현재는 개인 앱 키를 빌려 쓰는 중 — '오멍가멍' 팀 앱 등록 필요)
```

> 위 블록은 작업이 진행되는 대로 1~3번 표의 내용을 반영해 갱신한다.

---

## 변경 이력

| 날짜       | 내용                                                                                                                                                                    |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-04 | 문서 최초 작성. 목업 01·02·04·05·08 완료 시점 기준 정리                                                                                                                 |
| 2026-08-04 | 09 일정 편집 작업 — draggable-flatlist·reanimated 설치, `app/_layout.tsx`에 GestureHandlerRootView 추가                                                                 |
| 2026-08-04 | 09 머지(#8) 반영. 06·07 공유+이미지 저장 작업 — clipboard·sharing·view-shot·media-library 설치, `app.config.ts`에 사진 권한 추가, `.gitignore`에 `/ios`·`/android` 추가 |
| 2026-08-04 | 06·07 머지(#9) 반영. 03 지도 탭 연동 방식 비교(WebView vs 네이티브 SDK) 정리, 초안은 WebView로 결정                                                                     |
| 2026-08-04 | 03 지도 탭 작업 — react-native-webview 설치, `.env.example`에 `EXPO_PUBLIC_KAKAO_JS_KEY` 추가                                                                           |

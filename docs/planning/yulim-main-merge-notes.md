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
| `react-native-webview`                   | 13.16.1 | 지도 탭(목업 03)에서 카카오 지도 JS API 사용  | #10     |

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

**WebView 방식으로 구현 완료(#10).** 최종 방식은 팀 결정이 필요하며, 아래는 비교 근거다.

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

| 파일                                                                  | 변경 내용                                                                                                                                                 | 반영 PR |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `src/theme/colors.ts`                                                 | 시안 키 컬러 확장 토큰 추가 (primarySoft, leaf, sea, basalt 등)                                                                                           | #3      |
| `src/theme/typography.ts`                                             | 촘촘한 화면용 확장 스케일 추가 (sectionTitle, subtitle, label, caption, micro)                                                                            | #3      |
| `src/theme/radius.ts`                                                 | radius 토큰 신규 추가                                                                                                                                     | #3      |
| `src/theme/index.ts`                                                  | radius export 추가                                                                                                                                        | #3      |
| `src/theme/colors.ts`                                                 | 앱 기본 배경색을 화이트(`#FFFFFF`)로 변경 — 팀 결정 사항                                                                                                  | #6      |
| `app.config.ts`                                                       | `plugins` 배열에 `@react-native-community/datetimepicker` 추가                                                                                            | #5      |
| `app/_layout.tsx`                                                     | 최상단을 `GestureHandlerRootView`로 감싸기 (드래그 제스처 인식용)                                                                                         | #8      |
| `package.json` / `package-lock.json`                                  | draggable-flatlist, reanimated 추가                                                                                                                       | #8      |
| `app.config.ts`                                                       | `plugins`에 `expo-sharing` 추가, `expo-media-library`를 사진 접근 권한 문구와 함께 추가                                                                   | #9      |
| `package.json` / `package-lock.json`                                  | clipboard, sharing, view-shot, media-library 추가                                                                                                         | #9      |
| `apps/mobile/.gitignore`                                              | `/ios`, `/android` 추가 (expo prebuild 산출물 커밋 방지)                                                                                                  | #9      |
| `apps/mobile/.env.example`                                            | 신규. `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_KAKAO_JS_KEY`                                                                                                   | #10     |
| `.env.example`                                                        | Mobile 항목은 `apps/mobile/.env` 에 넣어야 한다는 안내 추가                                                                                               | #10     |
| `package.json` / `package-lock.json`                                  | react-native-webview 추가                                                                                                                                 | #10     |
| `app/_layout.tsx`                                                     | `Stack.Screen`에 `trips/[tripId]/add-schedule` 라우트 추가 (목업 10)                                                                                      | #14     |
| `app.config.ts`                                                       | `web.output` 을 `static` → `single` 로 변경 (웹 프리렌더 제거)                                                                                            | #15     |
| `src/theme/colors.ts`                                                 | **색상 토큰 전면 정리.** 중복 토큰 4개 통합, 신규 토큰 8개 추가, `categoryColors`·`brandColors`·`overlayColors`·`thumbnailPalette` 신설                   | #23     |
| 화면·컴포넌트 50개                                                    | 하드코딩된 색상 323건을 전부 theme 토큰 참조로 치환 (전 기능 대상)                                                                                        | #23     |
| `assets/brand/brand-symbol.png`                                       | **심볼 교체.** 하트 없는 버전으로 바꾸고 주황을 `#FF7A45`(`theme.primary`)로 보정, 203×240 로 축소                                                        | #26     |
| `src/components/layout/` (신규)                                       | **공통 상단 바 신설.** `AppHeader`(브랜드+알림+프로필), `ScreenTitleBar`(화면 제목+액션)                                                                  | #26     |
| `app/_layout.tsx`                                                     | `Stack.Screen` 에 `notifications` 라우트 추가                                                                                                             | #26     |
| 탭 5개 화면 헤더                                                      | 홈·루트 추천·챗봇·내 여행·마이페이지의 자체 헤더를 `AppHeader` 로 교체                                                                                    | #26     |
| `app/(tabs)/routes.tsx` → `routes/`                                   | 기본 탭바 숨김 제거. 폴더 라우트로 바꾸고 결과 화면을 탭 안으로 이동                                                                                      | #26     |
| `app/routes/result.tsx`                                               | `app/(tabs)/routes/result.tsx` 로 이동 (경로 `/routes/result` 는 그대로)                                                                                  | #26     |
| `app/_layout.tsx`                                                     | `routes/result` 라우트 등록 제거 (탭 스택으로 옮겨감)                                                                                                     | #26     |
| `src/components/layout/NotificationPopup.tsx` (신규)                  | 상단 바 알림 간이 팝업. `notificationPreview.mock.ts` 의 임시 목록을 보여준다                                                                             | #26     |
| `src/components/ui/SectionHeader.tsx`                                 | 중복이던 home 전용 버전과 통합. `style` prop 추가, 제목·링크를 토큰으로                                                                                   | 예정    |
| 기능별 `data/` 폴더                                                   | 목데이터는 `mocks/`, 정적 상수는 `constants/` 로 분리 (auth·chatbot·home·places·settings)                                                                 | 예정    |
| 목 파일 이름                                                          | `<이름>Mocks.ts` → `<이름>.mock.ts` 로 통일 (inquiries·notices·profile·travel-logs)                                                                       | 예정    |
| `src/components/ui/Card.tsx`·`StatTile.tsx`                           | **카드에 테두리 추가.** `borderWidth: 1` + `borderColor: colors.border`. 흰 배경 위 흰 카드라 카드 경계가 보이지 않던 문제                                | 예정    |
| `app/_layout.tsx`                                                     | `Stack.Screen` 에 라우트 4개 추가 (`travel-guides/index`·`travel-guides/preparation`·`saved/places`·`saved/routes`)                                       | 예정    |
| `src/components/feedback/EmptyState.tsx` (신규)                       | 목록이 비었을 때 쓰는 공통 안내. 아이콘·제목·설명 + 선택형 액션 버튼(`actionLabel`·`onPressAction`). 저장한 장소·저장한 코스·여행가이드·알림에서 사용     | 예정    |
| `src/components/layout/NotificationPopup.tsx`                         | 목데이터 정본이 `features/notifications/mocks/` 로 옮겨져 import 경로 변경. 팝업은 앞 2건만 보여준다                                                      | 예정    |
| `src/components/layout/notificationPreview.mock.ts`                   | `@deprecated` 재export 만 남김. 참조가 없으므로 **삭제해도 되는 파일**                                                                                    | 예정    |
| `features/places/screens/PlaceExplorerScreen.tsx`                     | 하트가 화면 상태(`useState`)여서 나가면 사라지던 것을 저장소 연동으로 교체                                                                                | 예정    |
| `features/route-recommendation/screens/RouteRecommendationScreen.tsx` | '코스 저장하기'가 단수 키(`saved-recommended-route`)를 덮어쓰던 것을 목록 저장으로 교체. `AsyncStorage` 직접 호출 제거                                    | 예정    |
| `features/profile/components/TravelSummarySection.tsx`                | 저장 개수를 목데이터(`mockActivitySummary`) 대신 실제 저장 목록에서 센다                                                                                  | 예정    |
| `features/trips/components/ScheduleTimelineItem.tsx`                  | **일정 카드를 루트 추천 결과 화면과 같은 가로형으로 교체.** 순번 배지를 4색 순환에서 `colors.primary` 단색으로 통일                                       | 예정    |
| `features/trips/components/ScheduleEditRow.tsx`                       | 순번 배지를 연한 주황에서 같은 주황 단색으로 통일                                                                                                         | 예정    |
| `features/trips/constants/placeThumbnail.ts` (신규)                   | 장소 사진이 없을 때 쓰는 카테고리별 이모지·파스텔 배경                                                                                                    | 예정    |
| `features/trips/components/DayChips.tsx`                              | 선택된 Day 칩 배경을 `colors.leaf`(올리브)에서 `colors.sea`(에메랄드)로. 루트 추천 Day 탭과 동일                                                          | 예정    |
| `features/trips/components/TripSummaryCard.tsx`                       | 요약 카드 맨 아랫줄(이동수단·반려동물·숙소) 글자를 `colors.leaf` 에서 `colors.seaDeep` 으로                                                               | 예정    |
| `src/components/ui/StatTile.tsx`                                      | **variant 를 2색에서 4색으로.** `mint`·`orange` → `blue`·`green`·`orange`·`yellow` 이고 값은 `categoryColors` 를 참조한다. 마이페이지에서만 쓰는 컴포넌트 | 예정    |
| `src/types/place.ts` (신규)                                           | **`PetPolicy` 정본을 features 밖으로 승격.** 내 여행·장소 탐색이 함께 쓴다. `trips/types/trip.ts` 가 재export 하므로 기존 import 경로는 그대로 동작한다   | 예정    |
| `src/components/domain/PetPolicyBadge.tsx` (신규)                     | 동반정책 배지를 공용으로 승격. `trips/components/PetPolicyBadge.tsx` 는 재export 만 남은 **삭제 가능 파일**                                               | 예정    |
| `features/trips/utils/tripFormat.ts`                                  | `getPetPolicyLabel` 라벨 정본이 `src/types/place.ts` 로 옮겨져 재export 로 바뀜. 함수 시그니처·import 경로 변화 없음                                      | 예정    |
| `assets/images/pets/` (신규)                                          | 몽이·코코 프로필 일러스트 (각 256×256 JPG, 15~17KB)                                                                                                       | 예정    |
| `assets/images/profile/default-user.jpg` (신규)                       | 사용자 기본 프로필 일러스트 (256×256, 10KB)                                                                                                               | 예정    |
| `features/profile/services/profileService.ts`                         | `DEFAULT_PROFILE_IMAGE` 를 빈 문자열에서 기본 일러스트로. 사진을 지워도 회색 아이콘 대신 일러스트가 남는다                                                | 예정    |

> **`app/_layout.tsx`는 충돌 위험이 큰 파일이다.** 다른 팀원도 라우트를 추가하면서 건드리게 된다.
> 변경 내용 자체는 기존 트리를 `GestureHandlerRootView`로 한 겹 감싼 것뿐이라
> 충돌이 나면 바깥 래퍼만 살리고 안쪽 `Stack.Screen` 목록은 양쪽 것을 합치면 된다.

### 색상 토큰 정리 — 팀원이 알아야 할 것

통합 시점에 화면마다 색이 제각각이라(같은 역할에 서로 다른 값 229종) theme 토큰으로 일괄 정리했다.
**앞으로 화면 파일에 hex 를 직접 쓰지 않는다.** 필요한 색이 없으면 `src/theme/colors.ts` 에 토큰을 먼저 추가한다.

| 바뀐 것     | 내용                                                                                                                          |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 없어진 토큰 | `orangeBg`→`primarySoft` / `orangeIcon`→`primary` / `mintBg`→`seaSoftLight` / `mintIcon`→`sea`                                |
| 새 토큰     | `primaryDeep` `primaryInk` `primarySoftStrong` `textStrong` `seaDeep` `seaSoftLight` `calendarSunday` `calendarSaturday`      |
| 새 묶음     | `categoryColors`(데이터용 색) / `brandColors`(소셜 로그인, **변경 금지**) / `overlayColors`(rgba·그림자) / `thumbnailPalette` |

눈에 띄게 달라지는 화면은 **루트 추천**이다. 주황을 `#FF7A00` 으로 쓰고 있었는데 팀 확정값인
`#FF7A45`(`colors.primary`)로 맞췄다. 루트 추천의 로컬 팔레트 객체(`palette`, `colors`)는
참조 코드를 건드리지 않으려고 남겨두었고, 값만 theme 토큰을 가리키도록 바꿨다 (파일 상단 TODO 참고).

지도 WebView 의 HTML 은 토큰을 직접 못 쓰므로 `buildKakaoMapDocument.ts` 의 `mapColors` 객체를
거쳐 문자열에 주입한다. 지도 색을 바꾸려면 그 객체를 고친다.

### 브랜드 심볼 — 팀원이 알아야 할 것

`assets/brand/brand-symbol.png` 를 교체했다. `src/config/brandAssets.ts` 를 거쳐 참조하므로
경로를 직접 쓰는 화면은 없고, 파일만 바뀌었다.

| 항목 | 변경 전               | 변경 후                             |
| ---- | --------------------- | ----------------------------------- |
| 도안 | 발바닥 안에 하트 있음 | 하트 없는 단순형                    |
| 주황 | `#EB9850`             | `#FF7A45` (`theme.primary` 와 동일) |
| 크기 | 215×240               | 203×240 (투명 여백 제거)            |

화면 색을 전부 `#FF7A45` 로 통일했는데 심볼만 다른 주황이라 나란히 놓이면 톤이 튀었다.
주황 계열 픽셀만 골라 시프트했고 잎(초록)·현무암(회색)은 원본 그대로다.

### 공통 상단 바 — 팀원이 알아야 할 것

헤더가 화면마다 달랐다. 높이 3종(54/48/가변), 알림 아이콘 크기 2종(23/21),
좌우 여백 3종(18/16/24), 브랜드형과 제목형 두 패턴 혼재, 심볼은 홈에만.
루트 추천은 심볼 대신 `Ionicons` 의 `paw` 아이콘을 쓰고 있었다.

**하단 탭 5개 화면은 이제 `src/components/layout/AppHeader` 를 쓴다.**

```
┌──────────────────────────────────┐
│ [심볼] 오멍가멍      [알림] [프로필] │  AppHeader (54, 모든 탭 공통)
├──────────────────────────────────┤
│ 내 여행                    [공유] │  ScreenTitleBar (48, 필요한 화면만)
└──────────────────────────────────┘
```

- 새 탭 화면을 만들면 `<AppHeader />` 를 **`ScrollView` 바깥**에 놓는다.
  안에 넣으면 스크롤할 때 같이 밀려 올라간다 (홈이 그랬다).
- 심볼과 '오멍가멍' 글자는 **홈으로 가는 버튼**이다. 어느 탭에서든 눌러서 홈으로 돌아올 수 있다.
- 화면 제목과 그 화면만의 버튼은 `<ScreenTitleBar title="..." right={...} />` 로 그 아래 놓는다.
- **프로필은 어느 화면에서든 마이페이지로 간다.** 화면별로 다르게 동작하지 않는다.
- 알림은 화면 성격에 따라 두 가지다. `notifications` prop 으로 고른다.

| 값              | 동작                             | 쓰는 화면                | 이유                                         |
| --------------- | -------------------------------- | ------------------------ | -------------------------------------------- |
| `screen` (기본) | `/notifications` 로 이동         | 홈, 마이페이지           | 둘러보는 화면이라 이동해도 잃을 게 없다      |
| `popup`         | `NotificationPopup` 을 겹쳐 띄움 | 루트 추천, 챗봇, 내 여행 | 입력·대화 중이라 화면을 떠나면 흐름이 끊긴다 |

```tsx
<AppHeader />                        // 홈, 마이페이지
<AppHeader notifications="popup" />  // 루트 추천, 챗봇, 내 여행
```

팝업 내용은 `src/components/layout/notificationPreview.mock.ts` 에 있다.
알림 API 가 생기면 이 파일을 Query 훅으로 바꾸고 `features/notifications/` 로 옮긴다.

- 상세 화면(여행 정보, 장소 상세 등)은 뒤로가기 헤더를 그대로 쓴다. 이번 통일 대상이 아니다.

`app/notifications.tsx` 는 `ComingSoonScreen` 을 띄운다. 알림 화면이 생기면 이 파일만 바꾸면 된다.

### 기능 폴더 구조 정리 — 팀원이 알아야 할 것

같은 성격의 파일이 기능마다 다른 폴더에 있었다. **파일 위치와 이름만 바뀌었고 내용은 그대로다.**

|           | 이전                                      | 이후                         |
| --------- | ----------------------------------------- | ---------------------------- |
| 목데이터  | `data/` 5개 기능 · `mocks/` 6개 기능      | **`mocks/`** 로 통일         |
| 목 파일명 | `inquiryMocks.ts` · `routes.mock.ts` 혼재 | **`<이름>.mock.ts`** 로 통일 |
| 정적 상수 | `data/` 안에 목데이터와 섞여 있음         | **`constants/`** 로 분리     |

`data/` 를 통째로 `mocks/` 로 바꾸지 않은 이유는, 그 안에 목데이터가 아닌 것이 섞여 있었기 때문이다.
`quickMenuItems`(홈 빠른 메뉴), `placeCategories`(장소 카테고리), `settingsMenuItems` 같은 값은
백엔드가 붙어도 계속 쓰는 **화면 설정값**이다. `mocks/` 에 두면 나중에 목데이터를 지울 때 같이 지워진다.

- **목데이터** = 백엔드 응답을 흉내 낸 것 → `mocks/<이름>.mock.ts`. API 연동 시 지운다
- **정적 상수** = 코드에 계속 남는 값 → `constants/<이름>.ts`
- **함수·로직** = `utils/`. `chatbotMapResponse.ts` 가 목이 아니라 판별 함수라 여기로 옮겼다

### 중복 컴포넌트 정리

**`SectionHeader` 2개는 통합했다.** `components/ui` 와 `features/home/components` 에 거의 같은 것이
따로 있었다. 공통 쪽으로 합치면서 화면이 조금 바뀐다.

|      | 홈                                | 마이페이지                                  |
| ---- | --------------------------------- | ------------------------------------------- |
| 제목 | 18pt `800` → 18pt `700`           | 16pt → **18pt** (`typography.sectionTitle`) |
| 링크 | 회색 → **주황**(`colors.primary`) | 16pt → **13pt** (`typography.label`)        |

바깥 여백은 화면마다 달라서 컴포넌트에서 빼고 `style` prop 으로 넘기도록 했다.

**`FormField` 2개는 이름만 같고 다른 컴포넌트였다.** 통합하지 않고 이름을 나눴다.

- `auth/components/FormField` → **`IconTextField`** (아이콘 + 입력창 + 비밀번호 토글)
- `inquiries/components/FormField` → **`LabeledField`** (라벨 + children 래퍼)

### 웹에서 버튼 중첩 오류 — 팀원도 알아야 할 규칙

`react-native-web` 은 `accessibilityRole="button"` 이 붙은 `Pressable` 을 진짜 HTML `<button>`
으로 렌더한다. HTML 은 **버튼 안에 버튼을 넣는 것을 금지**하므로(`no interactive content
descendant`), 이런 구조는 웹에서 오류 오버레이를 띄운다.

```tsx
// ❌ 웹에서 깨진다
<Pressable accessibilityRole="button">   {/* 카드 전체 */}
  ...
  <Pressable accessibilityRole="button">별</Pressable>
</Pressable>

// ✅ 형제로 두고 겹친다
<View style={styles.body}>
  <Pressable accessibilityRole="button" style={styles.card}>
    ...
    <View style={styles.saveSlot} />       {/* 자리만 확보 */}
  </Pressable>
  <Pressable accessibilityRole="button" style={styles.saveButton}>별</Pressable>
</View>
```

`saveButton` 은 `position: 'absolute'` 로 원래 자리에 얹으므로 **화면은 그대로다.**

- 네이티브(iOS·Android)에는 `<button>` 개념이 없어 중첩해도 동작한다. **웹에서만 드러난다**
- 네이티브에서도 좋은 구조는 아니다. 안쪽 버튼의 `hitSlop` 이 바깥 버튼 영역을 침범해
  가장자리를 누르면 엉뚱한 동작이 일어난다 (이번에 `hitSlop` 을 `padding` 으로 바꿔 해결)
- **바텀시트의 배경 `Pressable` 은 문제가 없다.** 자체 종료 태그(`/>`)로 두고 시트를
  형제로 놓는 구조라 중첩이 아니다. `WeatherSheet`·`TripShareSheet` 등이 이 방식이다

저장소 전체를 훑어 두 곳을 고쳤다. `ScheduleTimelineItem`(일정 카드 + 저장 별),
`PlaceCandidateCard`(장소 카드 + 선택 버튼). 둘 다 trips 담당 파일이다.

### 아직 남은 것

- **Screen 파일 17개가 `screens/` 밖에 있다** (travel-logs 7 · inquiries 3 · profile 3 · settings 2 · auth 1 · notices 1).
  다른 팀원이 작업 중인 파일이라 충돌 위험이 커서 이번엔 미뤘다. 회의에서 공지하고 다 같이 푸시한 뒤 옮기는 게 안전하다
- **API 계층 폴더가 `services/`(5개)와 `api/`(trips) 두 가지다.** 담당자가 작업 중이라 건드리지 않았다
- **바텀시트 구현이 두 가지다.** RN `Modal` 직접 구현 9곳, `@gorhom/bottom-sheet` 6곳. 팀 결정 필요
- **빈 기능 폴더 4개** — `pet-profile`, `reviews`, `travel-guides`, `weather`

### 루트 추천의 하단 바

루트 추천 탭만 하단 바 비율이 달랐다. `app/(tabs)/routes.tsx` 가 **기본 탭바를 숨기고**
(`tabBarStyle: { display: 'none' }`) `RouteBottomNavigation` 이라는 자체 하단 바를 그리고 있었다.
아이콘 22 / 글자 9 / 높이 62 로 기본 탭바와 수치가 달라 눈에 띄었다.

숨김을 풀고 자체 하단 바를 걷어내 다른 탭과 같은 탭바를 쓰도록 했다.
**탭 화면에서는 하단 바를 직접 그리지 않는다.**

결과 화면도 같은 문제가 있었다. 탭 **밖**(`app/routes/result.tsx`)에 있어서 진짜 탭바가 없었고,
역시 자체 하단 바를 그리고 있었다. **결과 화면을 루트 탭 안으로 옮겨** 해결했다.

```
app/(tabs)/routes.tsx          →  app/(tabs)/routes/_layout.tsx   (Stack)
app/routes/result.tsx          →  app/(tabs)/routes/index.tsx     (입력)
                                  app/(tabs)/routes/result.tsx    (결과)
```

`(tabs)` 는 주소에 안 들어가는 Route Group 이라 **경로는 `/routes`·`/routes/result` 그대로다.**
이동 코드는 한 줄도 바뀌지 않았다. 홈 탭이 `place-explorer` 를 다루는 방식과 같은 구조다.

`RouteBottomNavigation` 컴포넌트는 쓰는 곳이 없어져 삭제했다.
**하단 바가 필요한 화면은 탭 안에 두면 된다. 직접 그리지 않는다.**

같은 화면의 '루트 추천 정보 입력' 제목도 혼자 27pt 였다. `typography.title`(21pt)로 맞췄다.

`src/features/profile/components/ProfileHeader.tsx` 는 `ScreenTitleBar` 로 대체되어 삭제했다.

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
- app/_layout.tsx : 최상단을 GestureHandlerRootView로 감쌈 (드래그 제스처 인식용),
  Stack.Screen 에 trips/[tripId]/add-schedule 라우트 추가
- app.config.ts plugins :
  - @react-native-community/datetimepicker
  - expo-sharing
  - expo-media-library (사진 접근 / 사진첩 저장 권한 문구 포함)
- app.config.ts web.output : static → single
  static 은 모든 라우트를 Node 에서 프리렌더하는데, 그 과정에서 네이티브 전제 모듈이
  깨져 웹이 아예 뜨지 않았습니다. single 은 브라우저에서만 그리는 SPA 방식이라
  모바일 앱을 웹으로 미리 볼 때는 이쪽이 맞습니다.
  (웹을 정적 사이트로 내보낼 계획이 있다면 팀 논의가 필요합니다)
- apps/mobile/.gitignore : /ios, /android 추가
  (expo prebuild 가 만드는 217MB 네이티브 폴더가 커밋되지 않도록)
- apps/mobile/.env.example 신규 추가 (EXPO_PUBLIC_API_URL, EXPO_PUBLIC_KAKAO_JS_KEY)
  Expo 는 expo start 를 실행하는 폴더에서 .env 를 읽으므로 모바일 환경변수는
  저장소 루트가 아니라 apps/mobile/.env 에 넣어야 합니다. 루트 .env.example 에도 안내를 넣었습니다.

## 팀원 확인 사항

- pull 후 `cd apps/mobile && npm ci` 실행 필요
- 네이티브 권한이 추가되어 시뮬레이터에서 처음 실행할 때 사진 접근 권한을 물어봅니다
- 지도 탭을 보려면 apps/mobile/.env 에 EXPO_PUBLIC_KAKAO_JS_KEY 가 필요합니다.
  카카오 개발자 콘솔에 팀 앱 '오멍가멍'(ID 1533456)을 등록해두었고,
  제품 설정 > 카카오맵 > 사용 설정이 ON 이어야 합니다. 무료 쿼터도 이 앱에 배정돼 있습니다.
  개발 중에는 사이트 도메인 등록 없이 동작하며, 배포 도메인이 정해지면
  constants/map.ts 의 KAKAO_MAP_BASE_URL 에 넣고 콘솔에도 같은 주소를 등록하면 됩니다.

## places 담당자와 협의가 필요한 사항

- 일정 추가(목업 10)의 장소 검색은 원래 places 영역입니다.
  다만 'Day N 추천'·'내 숙소 근처'처럼 여행 정보를 알아야 하는 목록이 섞여 있어
  우선 trips 안에 임시 검색 UI를 만들었습니다 (features/trips/api/placeSearchApi.ts).
- 나중에 places 검색 화면을 재사용하기로 정해지면, 그 화면이 '선택 모드'를 지원하고
  결과로 장소 ID만(types/trip.ts 의 PlaceSelectionResult) 돌려주면 됩니다.
  trips 쪽은 searchPlaces 구현만 바꾸면 되고 화면은 그대로 둡니다.
```

> 위 블록은 작업이 진행되는 대로 1~3번 표의 내용을 반영해 갱신한다.

---

## 변경 이력

| 날짜       | 내용                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-04 | 문서 최초 작성. 목업 01·02·04·05·08 완료 시점 기준 정리                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-04 | 09 일정 편집 작업 — draggable-flatlist·reanimated 설치, `app/_layout.tsx`에 GestureHandlerRootView 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-04 | 09 머지(#8) 반영. 06·07 공유+이미지 저장 작업 — clipboard·sharing·view-shot·media-library 설치, `app.config.ts`에 사진 권한 추가, `.gitignore`에 `/ios`·`/android` 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-04 | 06·07 머지(#9) 반영. 03 지도 탭 연동 방식 비교(WebView vs 네이티브 SDK) 정리, 초안은 WebView로 결정                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-08-04 | 03 지도 탭 작업 — react-native-webview 설치, `.env.example`에 `EXPO_PUBLIC_KAKAO_JS_KEY` 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-08-04 | 03 지도 탭 머지(#10). 카카오 팀 앱 "오멍가멍"(ID 1533456) 등록 및 카카오맵 사용 설정 ON                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-05 | 10 일정 추가 작업 — 신규 설치 라이브러리 없음. `app/_layout.tsx`에 add-schedule 라우트 추가, places 담당자 협의 사항 기록                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-08-06 | 웹 실행 오류 수정 — `app.config.ts`의 `web.output`을 `single`로 변경, `expo-media-library` 호출을 `utils/saveImageToLibrary`(+`.web.ts`)로 분리. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-08-10 | 프론트 통합 후 디자인 색상 통일 — 하드코딩 색상 323건(값 229종)을 theme 토큰으로 일괄 치환. `colors.ts` 중복 토큰 4개 통합·신규 8개 추가, `categoryColors`·`brandColors`·`overlayColors`·`thumbnailPalette` 신설. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-08-12 | **main 머지 완료(#21).** 색상 통일은 #23 으로 `dev/integration` 에 반영 후 함께 올라갔다. 3번 표의 '예정' 항목을 실제 PR 번호(#14·#15·#23)로 갱신. `constants/map.ts`·`constants/share.ts` 의 옛 주석 정리 — 카카오 팀 앱 등록이 끝났는데 개인 키를 쓰는 중이라고 적혀 있던 부분을 사실대로 고치고, 배포 도메인 관련 TODO 를 한 곳으로 모았다.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-08-12 | 브랜드 심볼 교체 — 하트 없는 버전으로 바꾸고 주황을 `#FF7A45` 로 보정, 투명 여백 제거(203×240). 심볼 노출을 홈·로그인 두 곳으로 제한하고 챗봇 헤더에서 제거. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-08-12 | 공통 상단 바 신설 — `AppHeader`·`ScreenTitleBar` 를 `src/components/layout/` 에 추가하고 탭 5개 화면의 자체 헤더를 교체. 알림·프로필 아이콘에 동작 연결(`/notifications` 신규, `/profile` 이동). `app/_layout.tsx` 에 라우트 1개 추가. `ProfileHeader.tsx` 삭제. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-08-12 | 상단 바 후속 — 심볼·브랜드 영역을 홈 이동 버튼으로. 루트 추천 탭의 기본 탭바 숨김을 풀고 자체 `RouteBottomNavigation` 제거(결과 화면은 유지), '루트 추천 정보 입력' 제목을 27pt → `typography.title`(21pt)로 통일                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-08-12 | 루트 추천 결과 화면을 탭 안으로 이동(`app/(tabs)/routes/` 폴더 라우트로 재구성). 경로는 `/routes`·`/routes/result` 그대로. 자체 하단 바 `RouteBottomNavigation` 삭제 — 하단 바가 다섯 화면 모두 동일해졌다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-08-12 | 상단 바 동작 정리 — 프로필은 화면 불문 마이페이지로 통일(루트 추천의 반려동물 모달 제거, 편집은 선호 정보 섹션으로 계속 가능). 알림은 `notifications` prop 으로 화면 이동(홈·마이) / 팝업(루트·챗봇·내 여행) 선택. `NotificationPopup` 신설                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-12 | 기능 폴더 구조 정리 — `data/` 를 `mocks/`(목) 와 `constants/`(상수) 로 분리, 목 파일명을 `<이름>.mock.ts` 로 통일, `chatbotMapResponse` 를 `utils/` 로 이동. 중복 `SectionHeader` 통합, 이름만 같던 `FormField` 2개를 `IconTextField`·`LabeledField` 로 분리                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-08-12 | 웹 `<button>` 중첩 오류 수정 — `ScheduleTimelineItem`·`PlaceCandidateCard` 에서 카드 Pressable 안에 있던 버튼을 형제로 분리. 저장소 전체 스캔 결과 이 2곳뿐이었고 바텀시트 배경 패턴은 정상                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-17 | 마이페이지 카드 테두리 추가 — `ui/Card.tsx`·`ui/StatTile.tsx` 에 `borderWidth: 1` + `borderColor: colors.border` 적용. 배경(`#FFFFFF`)과 카드가 같은 색이고 `shadow.sm` 이 거의 보이지 않아 카드 경계가 사라지던 문제. `background` 는 팀 확정값이라 건드리지 않았다. `Card` 를 함께 쓰는 여행기록·문의·회원탈퇴 화면도 같이 바뀐다. 신규 라이브러리·토큰 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-08-17 | 신규 화면 라우트 일괄 추가 — 여행가이드(`/travel-guides`), 여행 준비 가이드(`/travel-guides/preparation`), 저장한 장소(`/saved/places`), 저장한 코스(`/saved/routes`), 알림(`/notifications` 을 `ComingSoonScreen` 에서 실제 화면으로 교체). 홈 빠른 메뉴의 'Log 만들기'는 화면이 이미 있어 연결만 했고, '내 캐릭터 만들기'는 설계 전이라 준비 중 화면을 유지했다. **용어** — 저장한 코스의 내부 이름은 가이드 11장에 따라 `route` 를 쓰고 화면 문구만 '코스'로 둔다. **역할 구분** — 여행 준비 가이드는 특정 여행과 무관한 일반 지식 콘텐츠이고, 여행별 준비물은 내 여행의 체크리스트 탭이 담당한다. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                     |
| 2026-08-17 | 저장 기능 연결 — `features/saved/` 신설(타입·`savedStorage`·TanStack Query 훅). 장소 탐색 하트, 루트 추천 '코스 저장하기', 저장 목록 화면, 마이페이지 개수를 하나의 저장소로 묶었다. **루트 추천은 단수 키를 쓰고 있어 코스를 하나만 저장할 수 있었고**, 마이페이지 개수는 목데이터라 실제 저장과 무관했다. 저장 위치는 AsyncStorage 이며 키는 `omeong-gameong.saved-places.<이메일>` · `omeong-gameong.saved-routes.<이메일>` 형태다. **로그아웃해도 지우지 않는다**(팀 결정). 대신 키에 계정을 물려 다른 계정으로 로그인해도 남의 목록이 보이지 않는다. 저장 API 가 준비되면 `savedStorage.ts` 구현만 갈아끼우고 훅·화면은 그대로 둔다. 신규 라이브러리 없음                                                                                                                                                                                                                                                 |
| 2026-08-17 | 내 여행 일정 카드를 루트 추천 결과 화면과 통일 — 세로 레일 + 세로형 카드를 가로형 카드로 바꿨다. 왼쪽 열(순번 + 시각) · 썸네일 · 본문 · 오른쪽 저장 버튼 순이고, 이동 정보는 세로선 + 이동수단 아이콘으로 맞췄다. **순번 배지 색** — `[primary, leaf, sea, basalt]` 를 순번 나머지로 돌려 쓰고 있어 색이 아무 뜻이 없었고 4번째(현무암)가 꺼져 보였다. 키 컬러 `colors.primary` 하나로 통일했다. 일정 편집(`ScheduleEditRow`)의 연한 주황도 같이 맞췄고, 지도 탭(`MapPlaceCard`)은 이미 주황 단색이라 그대로 뒀다. 공유 이미지(`TripShareCard`)는 흰 배경 인쇄용이라 연한 주황을 유지했다 — 팀 확인 필요. 장소 사진(`imageUrl`)이 아직 전부 null 이라 카테고리별 이모지 썸네일로 대체한다. 신규 라이브러리 없음                                                                                                                                                                                                |
| 2026-08-17 | 내 여행의 초록을 루트 추천과 맞춤 — 선택된 Day 칩을 `colors.leaf`(#4E7A3A 올리브)에서 `colors.sea`(#2BB8AC 에메랄드)로, 요약 카드 맨 아랫줄 글자를 `colors.seaDeep`(#188F7B)으로 바꿨다. **작은 글자에는 `sea` 대신 `seaDeep` 을 쓴다** — `sea` 는 흰 배경에서 대비가 부족하고, 루트 추천도 작은 초록 글자에 `deepMint`(=`seaDeep`)를 쓴다. 나머지 `leaf` 사용처(동반정책 배지·날씨 좋음 표시·관광지 카테고리·지도 마커 등)는 색으로 정보를 구분하고 있어 그대로 뒀다                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-08-17 | 마이페이지 타일 색을 4색으로 — 주황·민트 2색을 번갈아 쓰던 것을 홈 빠른 메뉴와 같은 `categoryColors` 4색으로 바꿨다. **성격이 같은 메뉴는 색도 같게** 맞췄다: 장소=주황, 여행 로그=파랑, 가이드=초록 은 홈 빠른 메뉴와 같은 색이고 저장한 코스만 노랑이다. 새 색 토큰은 만들지 않았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-08-17 | 프로필 이미지를 실제 그림으로 교체 — 몽이·코코·사용자 아바타가 `https://placehold.co/200x200` 회색 상자였다. 일러스트를 번들에 넣고 `Image.resolveAssetSource(require(...)).uri` 로 참조한다. `Pet.profileImage`·`User.profileImage` 타입은 `string` 그대로 두어 API 연동 시 서버 URL 로 바꾸기만 하면 되게 했다. 이미지는 원본(1254×1254, 2.3MB)을 얼굴 중심 정사각 크롭 후 256×256 JPG(10~~17KB)로 줄였다 — 아바타가 화면에서 52~~56px 이라 3배 해상도로 충분하다. 코코 품종을 러시안블루 → 코리안숏헤어로 고쳤다(사진이 고등어태비). **남은 것** — 몽이 품종이 `몰티즈` 인데 그림은 진돗개 계열이라 어긋난다. `travel-logs/mocks/travelLog.mock.ts` 의 `PET_IMAGE` 도 아직 placehold.co 다                                                                                                                                                                                                                  |
| 2026-08-17 | 즐겨찾기 아이콘을 하트로 통일 — 내 여행 일정 카드의 저장 버튼이 별(`star`)이었고 장소 탐색은 하트(`heart`)였다. 하트로 맞추고 꺼진 상태 색도 `textTertiary` → `textSecondary` 로 장소 탐색과 같게 했다. **평점 표시의 노란 별(`MapPlaceCard`·`PlaceCandidateCard`)은 다른 용도라 그대로 뒀다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-08-17 | 장소 상세 화면 구현(`/places/[placeId]`) — `ScreenPlaceholder` 만 있던 자리를 채웠다. **핵심 문제는 장소 데이터가 두 벌이고 id 체계가 다르다는 것**이었다 (장소 탐색 `hamdeok-beach` / 내 여행 `place-hyeopjae`). 가진 필드도 서로 달라 어느 한쪽만으로는 상세를 못 채운다. 목데이터를 합치는 대신 **어댑터**를 뒀다 — `places/api/placesApi.ts` 의 `getPlaceDetail(id)` 이 두 목데이터를 차례로 찾아 `PlaceDetail` 하나로 변환하고, 화면은 이 타입만 본다. 상대에게 없는 값은 `null` 이고 화면이 그리지 않는다. 장소 API 가 붙으면 이 함수만 실제 호출로 바꾸면 된다. 동반 정책은 아는 만큼만 보여준다 — `petPolicy` 가 있으면 배지, `petFriendly` 만 있으면 가능/불가 문구와 확인 안내를 띄운다. **용어 충돌 발견** — `PlaceCategory` 가 places(필터 칩 정의 객체)와 trips(장소 분류 union) 두 곳에 서로 다른 뜻으로 있다. 이번엔 건드리지 않았지만 가이드 11장 기준으로 정리 대상이다. 신규 라이브러리 없음 |
| 2026-08-17 | Log 만들기 뒤로가기 수정 — `NewMomentPhotoStepScreen` 의 나가기 경로가 `router.replace('/travel-logs')` 로 고정돼 있어, 홈 빠른 메뉴로 들어온 사람이 뒤로가기를 누르면 홈이 아니라 여행 로그 목록으로 튕겨 나갔다. `router.canGoBack()` 이면 `back()`, 아니면 목록으로 보내도록 바꿨다. 홈 빠른 메뉴에 이 화면을 연결하면서 생긴 문제다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-17 | 루트 추천 입력 화면 크기 통일 — 이 화면만 `fontSize` 를 41개 하드코딩(8~~14px)하고 있어 다른 화면(11~~18px)보다 한 단계 작은 스케일이었다. 40개를 typography 토큰으로 바꾸고, 카드 여백·모서리·터치 영역도 `spacing`·`radius` 토큰으로 맞췄다(17건). 남은 하드코딩 `fontSize: 25`·`34` 는 이모지라 그대로 뒀다. 색상은 #23 에서 이미 통일했고 이번에 크기가 끝나, 파일 상단의 과도기 TODO 를 '별칭 이름 정리'만 남기고 갱신했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

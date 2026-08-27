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
| `src/components/ui/SectionHeader.tsx`                                 | 중복이던 home 전용 버전과 통합. `style` prop 추가, 제목·링크를 토큰으로                                                                                   | #30     |
| 기능별 `data/` 폴더                                                   | 목데이터는 `mocks/`, 정적 상수는 `constants/` 로 분리 (auth·chatbot·home·places·settings)                                                                 | #30     |
| 목 파일 이름                                                          | `<이름>Mocks.ts` → `<이름>.mock.ts` 로 통일 (inquiries·notices·profile·travel-logs)                                                                       | #30     |
| `src/components/ui/Card.tsx`·`StatTile.tsx`                           | **카드에 테두리 추가.** `borderWidth: 1` + `borderColor: colors.border`. 흰 배경 위 흰 카드라 카드 경계가 보이지 않던 문제                                | #32     |
| `app/_layout.tsx`                                                     | `Stack.Screen` 에 라우트 4개 추가 (`travel-guides/index`·`travel-guides/preparation`·`saved/places`·`saved/routes`)                                       | #32     |
| `src/components/feedback/EmptyState.tsx` (신규)                       | 목록이 비었을 때 쓰는 공통 안내. 아이콘·제목·설명 + 선택형 액션 버튼(`actionLabel`·`onPressAction`). 저장한 장소·저장한 코스·여행가이드·알림에서 사용     | #32     |
| `src/components/layout/NotificationPopup.tsx`                         | 목데이터 정본이 `features/notifications/mocks/` 로 옮겨져 import 경로 변경. 팝업은 앞 2건만 보여준다                                                      | #32     |
| `src/components/layout/notificationPreview.mock.ts`                   | `@deprecated` 재export 만 남김. 참조가 없으므로 **삭제해도 되는 파일**                                                                                    | #32     |
| `features/places/screens/PlaceExplorerScreen.tsx`                     | 하트가 화면 상태(`useState`)여서 나가면 사라지던 것을 저장소 연동으로 교체                                                                                | #32     |
| `features/route-recommendation/screens/RouteRecommendationScreen.tsx` | '코스 저장하기'가 단수 키(`saved-recommended-route`)를 덮어쓰던 것을 목록 저장으로 교체. `AsyncStorage` 직접 호출 제거                                    | #32     |
| `features/profile/components/TravelSummarySection.tsx`                | 저장 개수를 목데이터(`mockActivitySummary`) 대신 실제 저장 목록에서 센다                                                                                  | #32     |
| `features/trips/components/ScheduleTimelineItem.tsx`                  | **일정 카드를 루트 추천 결과 화면과 같은 가로형으로 교체.** 순번 배지를 4색 순환에서 `colors.primary` 단색으로 통일                                       | #32     |
| `features/trips/components/ScheduleEditRow.tsx`                       | 순번 배지를 연한 주황에서 같은 주황 단색으로 통일                                                                                                         | #32     |
| `features/trips/constants/placeThumbnail.ts` (신규)                   | 장소 사진이 없을 때 쓰는 카테고리별 이모지·파스텔 배경                                                                                                    | #32     |
| `features/trips/components/DayChips.tsx`                              | 선택된 Day 칩 배경을 `colors.leaf`(올리브)에서 `colors.sea`(에메랄드)로. 루트 추천 Day 탭과 동일                                                          | #32     |
| `features/trips/components/TripSummaryCard.tsx`                       | 요약 카드 맨 아랫줄(이동수단·반려동물·숙소) 글자를 `colors.leaf` 에서 `colors.seaDeep` 으로                                                               | #32     |
| `src/components/ui/StatTile.tsx`                                      | **variant 를 2색에서 4색으로.** `mint`·`orange` → `blue`·`green`·`orange`·`yellow` 이고 값은 `categoryColors` 를 참조한다. 마이페이지에서만 쓰는 컴포넌트 | #32     |
| `src/types/place.ts` (신규)                                           | **`PetPolicy` 정본을 features 밖으로 승격.** 내 여행·장소 탐색이 함께 쓴다. `trips/types/trip.ts` 가 재export 하므로 기존 import 경로는 그대로 동작한다   | #32     |
| `src/components/domain/PetPolicyBadge.tsx` (신규)                     | 동반정책 배지를 공용으로 승격. `trips/components/PetPolicyBadge.tsx` 는 재export 만 남은 **삭제 가능 파일**                                               | #32     |
| `src/types/place.ts`                                                  | **`PetPolicy` 를 4종 → 5종으로.** `unknown`(정보 없음) 추가. 서버 `petPolicy.policyType` 과 1:1 대응                                                      | 예정    |
| `src/components/domain/PetPolicyBadge.tsx`                            | `BADGE_COLORS` 에 `unknown` 추가(회색). 없으면 서버가 `unknown` 을 내려줄 때 화면이 죽는다                                                                | 예정    |
| `features/trips/utils/tripFormat.ts`                                  | `getPetPolicyLabel` 라벨 정본이 `src/types/place.ts` 로 옮겨져 재export 로 바뀜. 함수 시그니처·import 경로 변화 없음                                      | #32     |
| `assets/images/pets/` (신규)                                          | 몽이·코코 프로필 일러스트 (각 256×256 JPG, 15~17KB)                                                                                                       | #32     |
| `assets/images/profile/default-user.jpg` (신규)                       | 사용자 기본 프로필 일러스트 (256×256, 10KB)                                                                                                               | #32     |
| `features/profile/services/profileService.ts`                         | `DEFAULT_PROFILE_IMAGE` 를 빈 문자열에서 기본 일러스트로. 사진을 지워도 회색 아이콘 대신 일러스트가 남는다                                                | #32     |
| `src/components/ui/StatTile.tsx`                                      | `StatTileVariant` 에 `purple` 추가. 마이페이지 타일이 4개에서 5개('내가 쓴 리뷰')로 늘어 색이 하나 더 필요했다. **새 색 토큰은 만들지 않았다** — 이미 있는 `categoryColors.purple` 을 참조한다 | #86    |
| `app/_layout.tsx`                                                     | `Stack.Screen` 2개 추가 — `places/[placeId]/reviews/[reviewId]/edit`(리뷰 수정), `reviews/my`(내가 쓴 리뷰)                                               | #86    |
| `.gitignore`                                                          | `design-assets/` 추가. 디자인 원본은 저장소에 넣지 않는다 — 용량이 크고 리뷰 대상이 아니다. **계속 untracked 로 떠서 `git add .` 사고의 표적이었다** | #90    |
| `src/services/apiError.ts`                                            | `getApiErrorDetail()` 추가(신규 export, 기존 동작 변화 없음). `__DEV__` 에서만 서버가 보낸 `detail` 원문을 돌려준다 — 422 처럼 이유가 본문에만 있는 오류를 화면에서 바로 읽기 위해서다. 파일 소유는 lucky 님 | #90    |
| `src/components/feedback/ConfirmModal.tsx` (신규)                     | **예/아니오 확인 창 공용화.** 같은 생김새의 모달을 네 벌 따로 들고 있었다(`LogoutConfirmModal`·`DiscardChangesModal`·`ReviewDeleteConfirmModal`·`TripDeleteConfirmModal`). 넷을 얇은 래퍼로 바꿔 **호출부는 하나도 안 고쳤다** | #91    |
| `src/hooks/useSafeBack.ts` (신규)                                     | 뒤로 가되 갈 곳이 없으면 지정한 화면으로 보낸다. `router.back()` 만 부르면 **웹에서 히스토리가 없을 때 죽는다** | #91    |

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
| `apps/api/app/db/session.py`                                          | **DB 세션 시간대를 `Asia/Seoul` 로 고정** (`connect_args`). 저장 방식(`timestamptz`) 변경이 아니라 **읽어올 때 표기만** KST(`+09:00`)로 통일한다. UTC 로 내려가면 앱이 `startDate` 앞 10글자를 자를 때 이른 아침 일정의 날짜가 하루 밀린다 | 예정    |
| `apps/api/scripts/seed_dev.py` (신규)                                 | 개발용 씨앗 데이터. 사용자·반려동물·장소 4곳·여행 1개(3일 / 일정 6개). 여러 번 돌려도 중복이 쌓이지 않는다. 테스트 계정 `00000000-0000-0000-0000-000000000001` / `seed@omeong.local` 은 **A 와 공유한 고정 값**              | 예정    |
| `apps/api/app/api/dependencies.py`                                    | **`get_current_user` 신설** (임시 구현 — 개발용 고정 사용자 반환). 인증 담당이 **함수 안쪽만** JWT 검증으로 바꾸면 엔드포인트는 수정이 없다. 테스트는 `dependency_overrides` 로 갈아끼운다. 타입 별칭 `CurrentUser` 제공 | 예정    |
| `Makefile`                                                            | `db-seed` 타깃 추가 — 씨앗 데이터는 컨테이너 기동 시 자동 실행하지 않고 이 명령으로만 심는다                                                                                                                              | 예정    |

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

> **이 블록은 "아직 main 에 안 올라간 것"만 담는다.** main PR 을 낼 때마다 비우고 다시 쓴다.
> 직전 내용(일정 추가·장소 상세 서버 연결 + 목데이터 4개 삭제)은 **PR #84 로 이미 main 에 반영되었다.**
> 2026-08-25 에 `git log --oneline origin/main..HEAD` 로 확인하고 다시 썼다.
>
> 현재 대상: **리뷰 API 5개 · 여행 관리 API 3개 연결 + 웹 호환 정리** (커밋 21개 / 파일 64개)
>
> **공통 파일 5개를 건드렸다.** 이번엔 앞선 PR 들과 달리 공용 컴포넌트가 늘었다.

````markdown
## 신규 설치 라이브러리

없습니다. 마이그레이션도 없습니다.

## 이번 PR 내용

### 리뷰 기능이 서버에 붙었습니다

`GET`·`POST /places/{placeId}/reviews`, `PATCH`·`DELETE /reviews/{reviewId}`,
`GET /users/me/reviews` 다섯 개를 연결했습니다. 세션 메모리 배열을 쓰던
`reviewService.ts` 를 버리고 내 여행·장소와 같은 3층 구조로 옮겼습니다.

화면 세 개가 새로 생겼습니다 — 리뷰 수정, 내가 쓴 리뷰(마이페이지 타일에서 진입),
그리고 리뷰 카드의 수정·삭제 줄(자기 리뷰일 때만 보입니다).

**장소 상세의 "리뷰 N개"가 틀리고 있었습니다.** 목록 길이로 세고 있었는데 서버는
20건씩 끊어 주므로 21번째부터 20에서 멈춥니다. 서버가 함께 주는 집계값으로 바꿨습니다.

### 여행 관리 API 3개와 '담기' 버그

`PATCH /routes`(수정)·`DELETE /routes`(삭제)·`PATCH /route-items`(시각·메모)를 이었습니다.
여행 삭제는 진입점이 없어 새로 만들었습니다(여행 정보 화면 맨 아래).

**'담기'가 서버에 저장되지 않고 있었습니다.** 일정 추가 화면에서 장소를 담으면 화면
캐시만 바뀌어서, 담긴 것처럼 보이지만 앱을 껐다 켜면 사라졌습니다.

**여행 정보 편집 칸을 8개에서 3개로 줄였습니다.** 서버가 받는 것은 제목·선호키워드·
메모뿐이고 나머지는 고쳐도 저장되지 않았습니다. 읽기 화면에서는 그대로 다 보입니다.
자세한 사정은 아래 협의 사항에.

### 웹에서 깨지던 것들을 정리했습니다

앱 등록 승인이 늦어지면 웹으로 심사를 받을 수 있어 별도로 훑었습니다.

**`Alert.alert` 은 웹에서 아예 뜨지 않습니다.** 이 때문에 **루트 추천 입력에서 숙소를
지울 수 없었고**(휴지통을 눌러도 무반응), 반려동물 수정 화면에서는 프로필이 사라졌을 때
**빈 폼에 갇혔습니다.** 확인이 필요한 것은 모달로, 알림은 화면 안 문구로 바꿨습니다.

**`router.back()` 도 웹에서 죽습니다.** 주소로 바로 들어오거나 새로고침하면 히스토리가
비어 화면에 갇힙니다. 공용 훅으로 처리했습니다.

내 여행 일정 카드의 하트에 `'API 연동 후 동작해요'` 개발용 안내가 남아 있어 저장 목록에
연결했습니다.

## 공통 파일 변경

- `src/components/feedback/ConfirmModal.tsx` (신규) — 예/아니오 확인 창 공용 컴포넌트.
  **앞으로 확인 창은 `Alert.alert` 대신 이걸 씁니다.** 기존 확인 모달 네 개
  (`LogoutConfirmModal`·`DiscardChangesModal`·`ReviewDeleteConfirmModal`·
  `TripDeleteConfirmModal`)는 이걸 감싸는 래퍼가 되어 **호출부 변경은 없습니다.**
- `src/hooks/useSafeBack.ts` (신규) — 뒤로 가되 갈 곳이 없으면 지정한 화면으로 보냅니다.
  **새 화면에 뒤로가기를 붙일 때 `router.back()` 대신 씁니다.**
- `src/components/ui/StatTile.tsx` — `purple` variant 추가. 마이페이지 타일이 5개가
  되면서 색이 하나 더 필요했습니다. 새 색 토큰은 만들지 않았고 기존 `categoryColors` 를
  참조합니다.
- `src/services/apiError.ts` — `getApiErrorDetail()` 신규 export. 기존 동작 변화 없습니다.
  개발 중에만 서버가 보낸 사유 원문을 돌려줍니다.
- `.gitignore` — `design-assets/` 추가. 커밋된 적 없는 폴더라 영향은 없습니다.

## 팀원 확인 사항

- **백엔드가 떠 있어야 리뷰·내 여행 화면에 데이터가 보입니다.** `make dev-local` +
  `make db-seed-local`. 서버 없이 UI만 볼 때 비는 것은 고장이 아닙니다.
- **웹에서도 확인해 주세요.** 이번 수정의 절반은 웹에서만 재현됩니다.
- `Alert.alert` 은 새로 쓰지 말아 주세요. 확인은 `ConfirmModal`, 알림은 화면 안 문구입니다.
  기존 것 중 사진 앨범 권한 안내 5곳과 `useTripShare` 7곳은 이번에 남겨뒀습니다
  (권한 안내는 웹에서 그 경로를 타지 않고, 공유는 배포 도메인이 정해져야 완성됩니다).

## 협의가 필요한 사항

- **`GET /place-tags` 와 `POST /places` 를 앱에 붙이지 않는 것으로 확정하고 싶습니다.**
  태그 필터 UI 도, 장소 등록 화면도 없고 만들 계획도 없습니다. "안 붙이기로 했다"를
  기록으로 남겨두면 나중에 빠진 채로 굳는 것을 막을 수 있습니다.
- **수동 여행 생성(`POST /routes`) 방식 확인이 필요합니다.** 명세에 `route_days` 를
  만드는 엔드포인트가 없어, 여행을 만들 때 기간만큼 날짜를 함께 만들도록 했습니다.
  유력안대로 만들다 걸린 것이라 확인받고 싶습니다.
- **공유 기능은 배포 도메인이 정해져야 완성됩니다.** `SHARE_BASE_URL` 이 아직 빈 값이고,
  공유받은 사람이 열 페이지도 없습니다. 일정만 알려주시면 그때 붙이겠습니다.
- **여행 정보에서 이동수단·여행스타일·반려동물을 고칠 수 있게 할지.** 서버
  `RouteUpdate` 에 `transport`·`pace` 를 추가하고 반려동물 수정 API 를 만들면 편집 칸이
  돌아옵니다. 기간과 숙소는 성격이 다릅니다 — 기간은 날짜 행을 만들고 지워야 하고,
  숙소는 저장된 값이 아니라 일정의 숙소 항목에서 뽑아낸 문구입니다.
- **리뷰 한 건만 가져오는 엔드포인트(`GET /reviews/{reviewId}`)가 있으면 좋겠습니다.**
  지금은 수정 화면이 장소별 목록에서 찾아 쓰는데, 목록에 페이지를 붙이면 21번째 이후
  리뷰는 수정 화면을 못 엽니다.
- **`StatTile` 의 작은 글자(라벨 13px / 숫자 10px)는 lucky 님이 의도적으로 정한 값입니다.**
  가이드의 "11px 미만 금지"와 어긋나 보이지만 홈 빠른 메뉴와 맞춘 것이라 그대로 뒀습니다.
  되돌리지 말아 주세요.

기존 안건(추천 방식 규칙 vs AI, `api-ci.yml` 에 PostgreSQL, 이용약관 조항,
`POST /uploads` 담당자, 서버 region 값과 앱 지역 칩 통일, 일정 날짜 이동 API,
`PlaceCategory` 라벨 두 벌, 이동수단 7종/4종, 담당 영역 겹침 규칙)은 그대로 남아 있습니다.
````

---


## 변경 이력

| 날짜       | 내용                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-04 | 문서 최초 작성. 목업 01·02·04·05·08 완료 시점 기준 정리                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-08-04 | 09 일정 편집 작업 — draggable-flatlist·reanimated 설치, `app/_layout.tsx`에 GestureHandlerRootView 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-08-04 | 09 머지(#8) 반영. 06·07 공유+이미지 저장 작업 — clipboard·sharing·view-shot·media-library 설치, `app.config.ts`에 사진 권한 추가, `.gitignore`에 `/ios`·`/android` 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-08-04 | 06·07 머지(#9) 반영. 03 지도 탭 연동 방식 비교(WebView vs 네이티브 SDK) 정리, 초안은 WebView로 결정                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-08-04 | 03 지도 탭 작업 — react-native-webview 설치, `.env.example`에 `EXPO_PUBLIC_KAKAO_JS_KEY` 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-08-04 | 03 지도 탭 머지(#10). 카카오 팀 앱 "오멍가멍"(ID 1533456) 등록 및 카카오맵 사용 설정 ON                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-08-05 | 10 일정 추가 작업 — 신규 설치 라이브러리 없음. `app/_layout.tsx`에 add-schedule 라우트 추가, places 담당자 협의 사항 기록                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-08-06 | 웹 실행 오류 수정 — `app.config.ts`의 `web.output`을 `single`로 변경, `expo-media-library` 호출을 `utils/saveImageToLibrary`(+`.web.ts`)로 분리. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-08-10 | 프론트 통합 후 디자인 색상 통일 — 하드코딩 색상 323건(값 229종)을 theme 토큰으로 일괄 치환. `colors.ts` 중복 토큰 4개 통합·신규 8개 추가, `categoryColors`·`brandColors`·`overlayColors`·`thumbnailPalette` 신설. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-08-12 | **main 머지 완료(#21).** 색상 통일은 #23 으로 `dev/integration` 에 반영 후 함께 올라갔다. 3번 표의 '예정' 항목을 실제 PR 번호(#14·#15·#23)로 갱신. `constants/map.ts`·`constants/share.ts` 의 옛 주석 정리 — 카카오 팀 앱 등록이 끝났는데 개인 키를 쓰는 중이라고 적혀 있던 부분을 사실대로 고치고, 배포 도메인 관련 TODO 를 한 곳으로 모았다.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-12 | 브랜드 심볼 교체 — 하트 없는 버전으로 바꾸고 주황을 `#FF7A45` 로 보정, 투명 여백 제거(203×240). 심볼 노출을 홈·로그인 두 곳으로 제한하고 챗봇 헤더에서 제거. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-08-12 | 공통 상단 바 신설 — `AppHeader`·`ScreenTitleBar` 를 `src/components/layout/` 에 추가하고 탭 5개 화면의 자체 헤더를 교체. 알림·프로필 아이콘에 동작 연결(`/notifications` 신규, `/profile` 이동). `app/_layout.tsx` 에 라우트 1개 추가. `ProfileHeader.tsx` 삭제. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-08-12 | 상단 바 후속 — 심볼·브랜드 영역을 홈 이동 버튼으로. 루트 추천 탭의 기본 탭바 숨김을 풀고 자체 `RouteBottomNavigation` 제거(결과 화면은 유지), '루트 추천 정보 입력' 제목을 27pt → `typography.title`(21pt)로 통일                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-08-12 | 루트 추천 결과 화면을 탭 안으로 이동(`app/(tabs)/routes/` 폴더 라우트로 재구성). 경로는 `/routes`·`/routes/result` 그대로. 자체 하단 바 `RouteBottomNavigation` 삭제 — 하단 바가 다섯 화면 모두 동일해졌다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-12 | 상단 바 동작 정리 — 프로필은 화면 불문 마이페이지로 통일(루트 추천의 반려동물 모달 제거, 편집은 선호 정보 섹션으로 계속 가능). 알림은 `notifications` prop 으로 화면 이동(홈·마이) / 팝업(루트·챗봇·내 여행) 선택. `NotificationPopup` 신설                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-08-12 | 기능 폴더 구조 정리 — `data/` 를 `mocks/`(목) 와 `constants/`(상수) 로 분리, 목 파일명을 `<이름>.mock.ts` 로 통일, `chatbotMapResponse` 를 `utils/` 로 이동. 중복 `SectionHeader` 통합, 이름만 같던 `FormField` 2개를 `IconTextField`·`LabeledField` 로 분리                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-08-12 | 웹 `<button>` 중첩 오류 수정 — `ScheduleTimelineItem`·`PlaceCandidateCard` 에서 카드 Pressable 안에 있던 버튼을 형제로 분리. 저장소 전체 스캔 결과 이 2곳뿐이었고 바텀시트 배경 패턴은 정상                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-08-17 | 마이페이지 카드 테두리 추가 — `ui/Card.tsx`·`ui/StatTile.tsx` 에 `borderWidth: 1` + `borderColor: colors.border` 적용. 배경(`#FFFFFF`)과 카드가 같은 색이고 `shadow.sm` 이 거의 보이지 않아 카드 경계가 사라지던 문제. `background` 는 팀 확정값이라 건드리지 않았다. `Card` 를 함께 쓰는 여행기록·문의·회원탈퇴 화면도 같이 바뀐다. 신규 라이브러리·토큰 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-17 | 신규 화면 라우트 일괄 추가 — 여행가이드(`/travel-guides`), 여행 준비 가이드(`/travel-guides/preparation`), 저장한 장소(`/saved/places`), 저장한 코스(`/saved/routes`), 알림(`/notifications` 을 `ComingSoonScreen` 에서 실제 화면으로 교체). 홈 빠른 메뉴의 'Log 만들기'는 화면이 이미 있어 연결만 했고, '내 캐릭터 만들기'는 설계 전이라 준비 중 화면을 유지했다. **용어** — 저장한 코스의 내부 이름은 가이드 11장에 따라 `route` 를 쓰고 화면 문구만 '코스'로 둔다. **역할 구분** — 여행 준비 가이드는 특정 여행과 무관한 일반 지식 콘텐츠이고, 여행별 준비물은 내 여행의 체크리스트 탭이 담당한다. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-08-17 | 저장 기능 연결 — `features/saved/` 신설(타입·`savedStorage`·TanStack Query 훅). 장소 탐색 하트, 루트 추천 '코스 저장하기', 저장 목록 화면, 마이페이지 개수를 하나의 저장소로 묶었다. **루트 추천은 단수 키를 쓰고 있어 코스를 하나만 저장할 수 있었고**, 마이페이지 개수는 목데이터라 실제 저장과 무관했다. 저장 위치는 AsyncStorage 이며 키는 `omeong-gameong.saved-places.<이메일>` · `omeong-gameong.saved-routes.<이메일>` 형태다. **로그아웃해도 지우지 않는다**(팀 결정). 대신 키에 계정을 물려 다른 계정으로 로그인해도 남의 목록이 보이지 않는다. 저장 API 가 준비되면 `savedStorage.ts` 구현만 갈아끼우고 훅·화면은 그대로 둔다. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-17 | 내 여행 일정 카드를 루트 추천 결과 화면과 통일 — 세로 레일 + 세로형 카드를 가로형 카드로 바꿨다. 왼쪽 열(순번 + 시각) · 썸네일 · 본문 · 오른쪽 저장 버튼 순이고, 이동 정보는 세로선 + 이동수단 아이콘으로 맞췄다. **순번 배지 색** — `[primary, leaf, sea, basalt]` 를 순번 나머지로 돌려 쓰고 있어 색이 아무 뜻이 없었고 4번째(현무암)가 꺼져 보였다. 키 컬러 `colors.primary` 하나로 통일했다. 일정 편집(`ScheduleEditRow`)의 연한 주황도 같이 맞췄고, 지도 탭(`MapPlaceCard`)은 이미 주황 단색이라 그대로 뒀다. 공유 이미지(`TripShareCard`)는 흰 배경 인쇄용이라 연한 주황을 유지했다 — 팀 확인 필요. 장소 사진(`imageUrl`)이 아직 전부 null 이라 카테고리별 이모지 썸네일로 대체한다. 신규 라이브러리 없음                                                                                                                                                                                                                                                                                                                                   |
| 2026-08-17 | 내 여행의 초록을 루트 추천과 맞춤 — 선택된 Day 칩을 `colors.leaf`(#4E7A3A 올리브)에서 `colors.sea`(#2BB8AC 에메랄드)로, 요약 카드 맨 아랫줄 글자를 `colors.seaDeep`(#188F7B)으로 바꿨다. **작은 글자에는 `sea` 대신 `seaDeep` 을 쓴다** — `sea` 는 흰 배경에서 대비가 부족하고, 루트 추천도 작은 초록 글자에 `deepMint`(=`seaDeep`)를 쓴다. 나머지 `leaf` 사용처(동반정책 배지·날씨 좋음 표시·관광지 카테고리·지도 마커 등)는 색으로 정보를 구분하고 있어 그대로 뒀다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-08-17 | 마이페이지 타일 색을 4색으로 — 주황·민트 2색을 번갈아 쓰던 것을 홈 빠른 메뉴와 같은 `categoryColors` 4색으로 바꿨다. **성격이 같은 메뉴는 색도 같게** 맞췄다: 장소=주황, 여행 로그=파랑, 가이드=초록 은 홈 빠른 메뉴와 같은 색이고 저장한 코스만 노랑이다. 새 색 토큰은 만들지 않았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-08-17 | 프로필 이미지를 실제 그림으로 교체 — 몽이·코코·사용자 아바타가 `https://placehold.co/200x200` 회색 상자였다. 일러스트를 번들에 넣고 `Image.resolveAssetSource(require(...)).uri` 로 참조한다. `Pet.profileImage`·`User.profileImage` 타입은 `string` 그대로 두어 API 연동 시 서버 URL 로 바꾸기만 하면 되게 했다. 이미지는 원본(1254×1254, 2.3MB)을 얼굴 중심 정사각 크롭 후 256×256 JPG(10~~17KB)로 줄였다 — 아바타가 화면에서 52~~56px 이라 3배 해상도로 충분하다. 코코 품종을 러시안블루 → 코리안숏헤어로 고쳤다(사진이 고등어태비). **남은 것** — 몽이 품종이 `몰티즈` 인데 그림은 진돗개 계열이라 어긋난다. `travel-logs/mocks/travelLog.mock.ts` 의 `PET_IMAGE` 도 아직 placehold.co 다                                                                                                                                                                                                                                                                                                                                                     |
| 2026-08-17 | 즐겨찾기 아이콘을 하트로 통일 — 내 여행 일정 카드의 저장 버튼이 별(`star`)이었고 장소 탐색은 하트(`heart`)였다. 하트로 맞추고 꺼진 상태 색도 `textTertiary` → `textSecondary` 로 장소 탐색과 같게 했다. **평점 표시의 노란 별(`MapPlaceCard`·`PlaceCandidateCard`)은 다른 용도라 그대로 뒀다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-08-17 | 장소 상세 화면 구현(`/places/[placeId]`) — `ScreenPlaceholder` 만 있던 자리를 채웠다. **핵심 문제는 장소 데이터가 두 벌이고 id 체계가 다르다는 것**이었다 (장소 탐색 `hamdeok-beach` / 내 여행 `place-hyeopjae`). 가진 필드도 서로 달라 어느 한쪽만으로는 상세를 못 채운다. 목데이터를 합치는 대신 **어댑터**를 뒀다 — `places/api/placesApi.ts` 의 `getPlaceDetail(id)` 이 두 목데이터를 차례로 찾아 `PlaceDetail` 하나로 변환하고, 화면은 이 타입만 본다. 상대에게 없는 값은 `null` 이고 화면이 그리지 않는다. 장소 API 가 붙으면 이 함수만 실제 호출로 바꾸면 된다. 동반 정책은 아는 만큼만 보여준다 — `petPolicy` 가 있으면 배지, `petFriendly` 만 있으면 가능/불가 문구와 확인 안내를 띄운다. **용어 충돌 발견** — `PlaceCategory` 가 places(필터 칩 정의 객체)와 trips(장소 분류 union) 두 곳에 서로 다른 뜻으로 있다. 이번엔 건드리지 않았지만 가이드 11장 기준으로 정리 대상이다. 신규 라이브러리 없음                                                                                                                                    |
| 2026-08-17 | Log 만들기 뒤로가기 수정 — `NewMomentPhotoStepScreen` 의 나가기 경로가 `router.replace('/travel-logs')` 로 고정돼 있어, 홈 빠른 메뉴로 들어온 사람이 뒤로가기를 누르면 홈이 아니라 여행 로그 목록으로 튕겨 나갔다. `router.canGoBack()` 이면 `back()`, 아니면 목록으로 보내도록 바꿨다. 홈 빠른 메뉴에 이 화면을 연결하면서 생긴 문제다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-08-17 | 루트 추천 입력 화면 크기 통일 — 이 화면만 `fontSize` 를 41개 하드코딩(8~~14px)하고 있어 다른 화면(11~~18px)보다 한 단계 작은 스케일이었다. 40개를 typography 토큰으로 바꾸고, 카드 여백·모서리·터치 영역도 `spacing`·`radius` 토큰으로 맞췄다(17건). 남은 하드코딩 `fontSize: 25`·`34` 는 이모지라 그대로 뒀다. 색상은 #23 에서 이미 통일했고 이번에 크기가 끝나, 파일 상단의 과도기 TODO 를 '별칭 이름 정리'만 남기고 갱신했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-08-17 | 루트 추천 입력을 단계별 노출로 변경 — 섹션 6개(여행일정·이동수단·숙소·반려동물·선호장소·여행속도)를 한 번에 다 보여주던 것을 **한 번에 하나씩** 펼치게 바꿨다. 아직 차례가 아닌 단계는 잠금(자물쇠·흐림), 끝낸 단계는 한 줄 요약으로 접히고 눌러서 다시 펼 수 있다. **숙소·여행속도는 `requestRecommendation` 검증에서 빠져 있어 선택 항목**이라 '건너뛰기' 버튼을 뒀다. 요약 카드와 '루트 추천받기' 버튼은 모든 단계를 지난 뒤에만 보인다. 임시 저장을 불러오면 이미 다 채운 상태이므로 전부 열린 채로 시작한다. 의미 없이 `1 / 1` 로 고정돼 있던 카운터는 제거했다(진행 표시는 두지 않기로 함)                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-08-17 | 루트 추천 입력에 '입력 초기화' 추가 — 단계별로 바꾸면서 접힌 단계가 생겨 전체를 되돌릴 방법이 없어졌다. **되돌릴 수 없는 동작이라 무게를 낮춰** 하단 맨 아래에 회색 작은 글씨로 뒀다(임시저장·나중에 버튼과 같은 줄에 두지 않음). 누르면 확인 모달을 띄우고, 승낙하면 draft 를 초기값으로 되돌리고 1단계로 접으며 **임시 저장본(`route-input-draft`)도 지운다** — 화면만 비우면 다시 들어왔을 때 지운 내용이 되살아나 혼란스럽다. 확인 창은 `Alert` 대신 이 파일의 기존 `utilityModal` 을 재사용했다 — `Alert` 는 웹에서 뜨지 않는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-08-17 | **오늘 작업을 `dev/yulim-main` 에 모두 반영.** PR #30(폴더 구조 정리·웹 버튼 중첩 수정), #32(신규 화면 5개·저장 기능·장소 상세·디자인 통일·프로필 이미지), #36(루트 추천 입력 크기 통일·단계별 노출·입력 초기화). 3번 표의 '예정' 을 실제 PR 번호로 갱신했다. lucky 님의 API 명세(#34·#35, `docs/api/` 13개)가 main 에 올라와 `dev/yulim-main` 에도 머지했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-08-18 | 동반 정책에 `unknown` 추가 — lucky 님 API 명세(`docs/api/places.md`, `type-mismatch-report.md`)를 오늘 작업과 대조했다. **정책이 5종으로 확정(2026-08-18)됐는데 우리 타입은 4종**이었고, 명세가 `PetPolicyBadge` 를 콕 집어 '서버가 `unknown` 을 내려주면 `BADGE_COLORS[petPolicy]` 가 undefined 가 되어 화면이 죽는다' 고 경고하고 있었다. 타입·라벨·배지 색을 5종으로 맞췄다. `unknown` 은 회색 '정보 없음' 배지이고 발바닥 이모지를 빼 다른 정책과 구분한다. **대조에서 확인한 나머지 차이는 이번에 고치지 않았다** — 표기법(snake_case), 필드명(`primaryImageUrl`·`reservationRequired`), `petPolicy` 가 객체라는 점 등은 `places/api/placesApi.ts` 어댑터 안에서 흡수할 것들이고, 필드명 규칙은 팀 회의 안건(문서 4-3)이라 합의 후에 손대야 한다. **참고** — 명세서는 PR #30 시점까지만 반영돼 있어 오늘 만든 타입 4개(`types/place.ts`, `places/types/placeDetail.ts`, `saved/types/saved.ts`, `notifications/types/notification.ts`)는 대조 대상이 아니고, 문서가 가리키는 `PetPolicyBadge` 경로도 옛 위치(`features/trips/components/`)다 |
| 2026-08-18 | API 명세 문서 3개 갱신(lucky 님 확인 후) — **사실 관계가 바뀐 부분만** 고쳤다. ① `PetPolicyBadge` 경로를 `features/trips/components/` → `src/components/domain/` 으로 (3개 문서에 걸쳐 있었다), ② `unknown` 미반영 경고를 '반영 완료' 로 바꾸고 README 의 '앱 코드 수정이 필요한 것' 목록에서 제거, ③ `type-mismatch-report.md` 부록에 PR #32·#36 신규 타입 4개를 '대조 안 함' 으로 추가. **분석·판단·회의 안건은 건드리지 않았다** — 문서 소유는 lucky 님이다. 변경 이력에 작성자를 남겼다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-08-18 | 5번 항목(main PR 본문) 재작성 — #21·#26 으로 이미 main 에 올라간 내용이 그대로 남아 있어 **아직 main 에 없는 것(PR #32·#36·#37)만** 담도록 비우고 다시 썼다. 이 블록은 main PR 을 낼 때마다 비우고 다시 쓰는 것이라는 안내도 함께 넣었다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-08-21 | **백엔드 B 파트(장소·리뷰·여행) 착수.** 씨앗 데이터 스크립트(`apps/api/scripts/seed_dev.py`) 신설 — 사용자·반려동물·장소 4곳·여행 1개(3일 / 일정 6개)를 심는다. 프론트 목데이터(`trips.mock.ts`)와 같은 이름·좌표를 써서 API 연동 시 화면을 눈으로 대조할 수 있게 했다. **시간대** — `timestamptz` 는 절대 시각을 담으므로 저장은 처음부터 정확했고 psql 이 UTC 로 보여주던 것뿐이었다. 저장 방식은 그대로 두고 엔진 `connect_args` 로 **세션 시간대만** `Asia/Seoul` 로 맞췄다. 명세(`docs/api/README.md` 6장)가 `+09:00` 표기를 쓰고, UTC 로 내리면 이른 아침 일정에서 날짜가 하루 밀린다. **테스트 계정** — id `00000000-0000-0000-0000-000000000001` / `seed@omeong.local` 을 A 와 공유해 회원가입 API 와 충돌하지 않게 했다. **에러 메시지는 한국어로 확정** (`README.md` 8장의 '첫 도메인 구현 시 정한다' 항목) — 단 `422` 는 FastAPI 자동 생성이라 영문이고, 앱이 `detail` 이 배열이면 자기 문구를 쓴다. **5번 항목은 아직 비우지 않았다** — 오늘 작업을 마치고 main PR 을 낼 때 다시 쓴다 |
| 2026-08-22 | **내 여행 화면을 여행 조회 API 에 연결.** `tripsApi.ts` 의 목데이터 호출을 `GET /routes` · `GET /routes/{routeId}` 로 교체하고, 서버·앱 타입 차이를 흡수하는 `api/routeAdapter.ts` 와 서버 응답 타입 `types/routeApi.ts` 를 신설했다. **훅·화면은 한 줄도 고치지 않았다** — 장소 상세(`placesApi.ts`)에서 쓴 어댑터 방식과 같다. 흡수한 차이: `startAt`(시각) → `startDate`(날짜), `sortOrder` 0부터 → `order` 1부터, `itemType` → `PlaceCategory`, 숙소 요약을 일정에서 추출, `pace` → 여행 성향 문구. 서버에 없는 값(날씨·이동거리·동반정책·평점·이동시간)은 빈 값으로 두어 화면이 그리지 않는다. **신규 라이브러리·공통 파일 변경 없음.** 다만 팀원이 pull 후 백엔드를 띄우지 않으면 내 여행 탭이 비므로 5번 항목에 안내를 넣었다. `trips.mock.ts` 는 **지우면 안 된다** — `features/places/api/placesApi.ts` 가 장소 상세 어댑터에서 아직 쓴다 |
| 2026-08-22 | **최신 main 을 받아와 합침(lucky 님 내 여행 목록 화면 PR #53·#54).** 충돌은 `api/tripsApi.ts` 한 파일 — 내 API 호출 구현을 살리고 `getLatestTrip` 을 제거했다(목록 화면이 생겨 "가장 최근 여행 하나"가 불필요해졌다). 합친 뒤 **lucky 님 목록 화면이 곧바로 실서버를 부른다** — `useTrips()` → `getTrips()` → `GET /routes`. 지금까지 쓰는 화면이 없던 목록 엔드포인트가 처음으로 화면을 가졌다. 화면에 씨앗 여행 1건만 뜨는 것으로 확인. **5번 항목을 현재 기준으로 다시 썼다** — PR #32·#36·#37 내용이 이미 main 에 반영됐는데 그대로 남아 있었다(`git diff --name-only origin/main...HEAD` 로 실제 파일을 확인). 이번 PR 의 공통 파일 변경은 **Makefile 의 db-seed 타깃 하나뿐**이고, 가영님 Docker/RDS 작업과 겹치는 유일한 지점이다 |
| 2026-08-23 | **여행 편집·장소·리뷰 API 29개 추가(백엔드만).** 일정 편집 4개·여행 관리 4개·체크리스트 4개·메모 4개·장소 8개·리뷰 5개. **앱 파일과 공통 파일은 하나도 건드리지 않았고 Alembic revision 도 없다** — 전부 이미 있는 테이블을 쓴다. 소유권 확인은 `services/route_access.py` 한 곳으로 모았다(없는 것은 404, 남의 것은 403 — 합치면 남의 여행 id 존재 여부가 새어 나간다). **순번(sort_order)은 두 번에 나눠 쓴다** — UNIQUE(route_day_id, sort_order) 를 PostgreSQL 이 행마다 즉시 검사해서 0·1·2 를 1·2·3 으로 한 번에 올리면 실패한다. 겹칠 수 없는 높은 구간으로 피했다가 0 부터 내려앉힌다. **GET /places 는 공식 장소만** 내린다(`created_by_user_id IS NULL`) — 한 줄만 빠뜨려도 남이 등록한 장소가 이름·좌표째로 검색에 섞인다. 거리는 PostGIS 없이 하버사인으로 계산하고 `least(1, ...)` 로 감쌌다(같은 좌표 조회 시 부동소수점 오차로 acos 가 터진다). 테스트 48개 신설, **TEST_DATABASE_URL 이 있을 때만** DB 테스트가 돈다(settings.database_url 을 자동으로 쓰면 공유 RDS 를 건드리게 된다). 5번 항목을 현재 기준으로 다시 썼다 — PR #61 내용이 그대로 남아 있었다 |
| 2026-08-23 | **수동 여행 생성 API + 앱 5개 화면 연결(오후).** 오전 PR #66 에 이어 `POST /routes` 를 유력안대로 만들었다 — 여행 껍데기만 만들고 **날짜(route_days)는 서버가 기간만큼 미리 만든다**(일정 추가가 routeDayId 를 요구하는데 날짜를 만드는 API 가 명세에 없다). 여행 상세의 빈 칸이던 `logCount` 와 장소의 `rating`·`reviewCount`·`petPolicyType` 을 채웠다 — 오전에 만든 집계식을 그대로 썼다. **앱은 다섯 곳이 목데이터를 버렸다** — 장소 목록·즐겨찾기·일정 편집 저장·체크리스트·메모. **즐겨찾기만 바꿀 수 없었다**: 목데이터 id 가 `hamdeok-beach` 같은 문자열이고 서버는 UUID 라, 장소 목록부터 서버로 옮겨야 했다. **공통 파일 `src/types/place.ts` 에 `toPetPolicy()` 를 추가**해 장소 탐색과 내 여행이 같은 변환을 쓰게 했다. 어댑터가 흡수한 차이 — 미터→km, 서버 category 코드→한글 라벨(안 그러면 분류 칩 필터가 통째로 안 먹는다), 서버 region 자유 문자열→앱 칩 6종(못 찾으면 null, 억지로 끼우면 엉뚱한 장소가 섞인다). **날짜 이동은 DELETE 후 POST 다** — 서버에 이동 API 가 없어서이고, 추천 점수·이유는 따라가지 못한다(안건). 순서 저장 때는 **화면에서 걸러진 좌표 없는 일정까지 챙긴다** — 순서 API 가 그 날짜 전체를 요구해서 화면이 아는 것만 보내면 422 다. 체크박스는 낙관적 갱신(왕복을 기다리면 한 박자 늦게 움직인다). 씨앗에 체크리스트 10개·메모 2개를 넣었다 — 없으면 '연결 안 됨'과 '데이터 없음'이 구분되지 않는다. `mocks/checklist.mock.ts`·`memos.mock.ts` 는 참조가 0 이 됐지만 이번엔 지우지 않았다. 5번 항목을 오후 기준으로 다시 썼다 — 협의 안건이 5건 늘었다 |
| 2026-08-24 | 5번 항목을 갱신 — 직전 내용(PR #74)은 main 반영 완료. 이번 대상은 일정 추가(장소 검색)·장소 상세 서버 연결과 목데이터 4개 삭제. 협의 사항에 분류 코드 매핑·리뷰 화면 연동 주체·RDS 실데이터 출처 3건 추가 |
| 2026-08-25 | **리뷰 API 5개를 앱에 연결.** `GET`·`POST /places/{placeId}/reviews`, `PATCH`·`DELETE /reviews/{reviewId}`, `GET /users/me/reviews`. `services/reviewService.ts` 의 세션 메모리 배열을 버리고 `api/reviewsApi.ts`+`api/reviewAdapter.ts`+`types/reviewApi.ts` 3층으로 나눴다(내 여행·장소와 같은 방식). **서버 리뷰 응답에는 `placeId` 가 없다** — 장소별 목록 엔드포인트라 서버 쪽에선 자명하지만 앱은 캐시 키로 쓰므로 어댑터가 요청에 쓴 값을 넣는다. **개수는 반드시 `summary.totalCount` 를 쓴다** — 목록은 20건씩 오는 한 페이지라 장소 상세의 '리뷰 N개'가 `items.length` 였고 21번째부터 어긋난다. **리뷰가 바뀌면 장소 캐시도 함께 무효화한다**(`hooks/reviewCache.ts`) — 장소의 평점·리뷰수는 저장값이 아니라 조회할 때마다 세는 집계라 리뷰 하나에 목록·상세 숫자가 같이 달라진다. 사진은 이미 올라간 URL 과 새 로컬 URI 를 구분해 **새것만** 업로드한다(수정할 때마다 전부 다시 올리면 같은 파일이 S3 에 쌓인다). 수정은 사진 **전체 목록**을 보낸다 — 서버가 받은 배열로 통째로 갈아끼운다. **화면 3개가 새로 필요했다** — 리뷰 수정(`ReviewEditScreen`), 내가 쓴 리뷰(`MyReviewsScreen`), 그리고 `ReviewCard` 의 수정·삭제 줄(`isMine` 일 때만). 작성·수정이 입력 항목이 같아 `components/ReviewForm.tsx` 로 합쳤다. **리뷰 한 건만 가져오는 엔드포인트가 없어** 수정 화면은 장소별 목록에서 찾아 쓴다 — 목록에 페이지를 붙이면 함께 손봐야 한다(안건). 삭제 확인은 `Alert` 대신 모달이다(웹에서 안 뜨는데 되돌릴 수 없는 동작이다). 429(같은 장소 30일 재작성)는 lucky 님이 `apiError.ts` 에 문구를 이미 만들어둬 그대로 쓴다. **공통 파일 2개 변경** — `StatTile` 에 `purple` variant, `app/_layout.tsx` 에 라우트 2개. 신규 라이브러리 없음. `services/reviewService.ts`·`mocks/review.mock.ts` 는 참조가 0 이 되어 삭제 대상이다 |
| 2026-08-25 | **여행 관리 API 3개 연결 + '담기' 버그 수정.** `PATCH /routes`(여행 수정) · `DELETE /routes`(삭제) · `PATCH /route-items`(시각·메모). **'담기'가 서버에 저장되지 않고 있었다** — `useAddSchedule` 이 `queryClient.setQueryData` 로 화면 캐시만 바꿔서, 담은 것처럼 보이지만 앱을 껐다 켜면 사라졌다. 엔드포인트는 이미 `tripsApi.addRouteItem` 에 있었고 훅만 연결하면 됐다. 시트를 먼저 닫고 낙관적으로 '담김' 표시를 한 뒤 실패하면 되돌린다(왕복을 기다리면 한 박자 늦게 닫혀 눌린 건지 알 수 없다). **여행 정보 편집 칸을 8개에서 3개로 줄였다** — 서버 `RouteUpdate` 가 받는 것은 제목·선호키워드·메모뿐이고 나머지 5개는 고쳐도 저장되지 않았다. 그중 이동수단(`transport`)·여행스타일(`pace`)·반려동물은 **서버가 받게 되면 돌아올 것**이고, 기간은 날짜 행(`route_days`)을 만들고 지워야 해서, 숙소는 **저장된 값이 아니라 일정의 숙소 항목에서 뽑아낸 문구**라 여기서 고칠 것이 아니다. `components/DateRangeField.tsx`·`components/PetEditRow.tsx` 는 돌아올 때 다시 쓰려고 **지우지 않고 남겼다**(지금은 참조 0). **여행 삭제는 진입점 자체가 없어 새로 만들었다** — 여행 정보 화면 맨 아래 회색 작은 글씨(되돌릴 수 없는 동작이라 무게를 낮춘다). 확인은 `Alert` 이 아니라 모달이고, **여행기록·사진은 지워지지 않는다는 것을 문구로 알린다**(서버가 `travel_logs.route_id` 만 비운다). 삭제 후에는 `router.replace('/trips')` — 뒤로 가면 방금 지운 여행의 상세로 돌아간다. **시각·메모 수정은 편집 화면의 draft 에 얹었다** — 즉시 반영이 아니라 저장 버튼 한 번으로 묶인다. `scheduleSync` 가 제자리에 남은 항목만 비교해 PATCH 하고, 옮긴 항목은 새로 만들 때 값을 함께 넣는다. `startsAt` 은 날짜와 함께 `+09:00` 을 붙여 보낸다(시각만으로는 어느 날인지 모르고, 빼면 아침 일정이 전날로 밀린다). **화면에서 확인하다 세 가지가 더 나왔다.** ① **시각 수정이 422 로 거절당하고 있었다** — `PATCH /route-items` 는 고친 `startsAt` 과 **기존** `endsAt` 을 함께 검사하는데 `startsAt` 만 보냈다. 씨앗 일정은 `endsAt = startsAt + 체류시간` 이라 시각을 뒤로 옮기는 순간 끝이 시작보다 앞선다. **머문 시간을 유지한 채 종료 시각도 같이 민다**(앱에 종료 시각 개념이 없어 사용자가 정할 방법이 없고, 원래 머물던 만큼 머문다고 보는 것이 가장 덜 놀랍다). 시각을 지우면 종료 시각도 함께 지운다. ② **그 거절이 웹에서 조용히 삼켜지고 있었다** — 일정 편집의 저장 실패·편집 취소 안내가 `Alert.alert` 였고 **웹에서는 뜨지 않는다.** 저장 실패는 인라인 배너로, 편집 취소는 `DiscardChangesModal` 로 바꿨다. C-3 에 남아 있던 '`Alert` 가 웹에서 안 뜬다' 의 한 건이 여기서 정리됐다. ③ **`router.back()` 이 웹에서 죽는다** — 주소로 바로 들어오면 히스토리가 없어 `GO_BACK was not handled by any navigator` 가 뜬다. 일정 추가·일정 편집 두 화면에 `canGoBack()` 확인을 넣고 없으면 여행 상세로 보낸다. **공통 파일 2개 변경** — `.gitignore` 에 `design-assets/` 추가(노트 04부터 네 번째 밀리던 항목), `src/services/apiError.ts` 에 `getApiErrorDetail()` 추가. 신규 라이브러리 없음 |
| 2026-08-25 | **웹에서만 깨지던 것들 정리.** 앱 스토어 승인이 늦어지면 **웹으로 심사**를 받을 수 있어, 웹에서 안 되는 기능을 남겨둘 수 없다는 팀 확인에 따른 작업이다. **`Alert.alert` 은 웹에서 아예 뜨지 않는다.** 저장소를 훑어 16곳을 성격별로 나눴다 — ① **확인이 필요한 것**(웹에서 기능이 죽음): 루트 추천 입력의 숙소 삭제(눌러도 아무 일이 없어 **숙소를 지울 수 없었다**), 반려동물 수정의 '프로필을 찾을 수 없어요'(확인을 눌러야 나가는데 창이 안 떠 **빈 폼에 갇혔다** → 화면 안 `EmptyState` 로 바꿈). ② **실패 알림**(실패해도 무반응): 로그아웃 실패, 여행 로그 저장 실패 → 화면 안 문구로. ③ **미연결 안내**: 로그인 화면의 '준비 중'·'추후 연동' → 화면 안 문구로. **심사에서 가장 먼저 보는 화면이라 무반응이면 고장으로 읽힌다.** ④ **사진 앨범 권한 안내 5곳과 `useTripShare` 7곳은 그대로 뒀다** — 권한 안내는 웹에서 그 경로를 타지 않고(권한 개념이 없다), 공유는 배포 도메인이 정해져야 완성되는 기능이라 그때 함께 본다. **확인 창 네 벌을 하나로 합쳤다** — `components/feedback/ConfirmModal.tsx` 신설, 기존 네 개는 문구만 담은 얇은 래퍼가 됐다(호출부 변경 없음). **`router.back()` 이 웹에서 죽는 문제**도 같이 봤다. 주소로 바로 들어오거나 새로고침하면 히스토리가 비어 `GO_BACK was not handled by any navigator` 가 뜬다. `hooks/useSafeBack.ts` 를 만들어 설정·프로필 수정·반려동물·여행 로그 헤더에 적용했다(`components/ui/ScreenHeader` 는 이미 처리돼 있었다). **그리고 내 여행 일정 카드의 하트를 서버에 연결했다** — `'저장 기능은 API 연동 후 동작해요'` 라는 개발용 Alert 이 그대로 남아 있었고, 웹에서는 그마저 안 떴다. 저장은 **장소 단위**라 일정 id 가 아니라 `place.id` 를 넘기고, 하트 상태는 `features/saved` 의 저장 목록에서 판단한다 (`ScheduleItem.isSaved` 는 어댑터가 알 수 없어 늘 false 다). **공통 파일 2개 신설** — `ConfirmModal`, `useSafeBack`. 신규 라이브러리 없음 |
| 2026-08-25 | **최신 main 을 받아와 합치고 5번 항목을 다시 썼다.** lucky 님 PR #88·#89(홈 빠른 메뉴 정리·마이페이지 디자인 통일)와 겹친 파일은 셋(`app/_layout.tsx`·`StatTile.tsx`·`TravelSummarySection.tsx`)이고 **실제 충돌은 하나**였다 — 같은 자리에 lucky 님은 가이드 아이콘을 바꾸고 나는 '내가 쓴 리뷰' 타일을 넣었다. 양쪽을 모두 살렸다. **`StatTile` 의 작은 글자(라벨 13px / 숫자 10px)는 lucky 님이 의도적으로 정한 값**이다 — 가이드의 '11px 미만 금지'와 어긋나 보여 확인했더니 홈 빠른 메뉴와 맞춘 것이었다. **되돌리지 말 것.** 5번 항목의 직전 내용(PR #84)은 이미 main 에 반영돼 비우고 다시 썼다 |

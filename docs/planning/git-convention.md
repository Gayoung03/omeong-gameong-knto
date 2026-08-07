# 오멍가멍 Git 컨벤션

작성일: 2026-08-07 · 대상 레포: `Gayoung03/omeong-gameong-knto`

---

## 1. 브랜치 전략

모노레포 하나를 함께 쓰고, 사람마다 개인 통합 브랜치를 둡니다.

```
main
 └─ dev/<이름>-main          개인 통합 브랜치 (gayoung / jihyun / lucky / yulim)
     └─ work/<이름>/<type>/<short-description>   실제 작업 브랜치
```

PR은 2단계로 올립니다.

1. `work/...` → `dev/<이름>-main` (본인이 확인 후 머지)
2. `dev/<이름>-main` → `main` (**팀원 1명 이상 승인 필요**)

`type` 은 커밋 태그와 동일하게 `feat` / `fix` / `refactor` / `style` / `docs` / `test` / `chore` 를 씁니다.

### 하지 말 것

- `main` 에 직접 push
- 개인 통합 브랜치에서 직접 작업
- 한 브랜치에서 여러 기능 작업
- `package-lock.json` 임의 삭제

### 이어서 작업하는 순서

```bash
git switch dev/<이름>-main && git pull
git switch -c work/<이름>/feat/<다음-작업>
# 작업 → lint/typecheck → 커밋 → push → PR(base: dev/<이름>-main)
```

---

## 2. 커밋 메시지

| 태그 | 내용 | 비고 |
| --- | --- | --- |
| `feat` | 새로운 기능 추가 | |
| `fix` | 버그 수정 | |
| `refactor` | 리팩토링 | 코드 구조 수정 |
| `style` | 코드 형식, 세미콜론 | 디자인 가이드 |
| `docs` | 문서 추가·수정·삭제 | |
| `test` | 테스트 코드 추가·수정·삭제 | |
| `chore` | 기타 변경사항, 세팅 관련 | |

형식은 `<type>: <작업 내용>` — 예) `feat: 내 여행 지도 탭 추가`

### ⚠️ 커밋은 나누어서

한 커밋에 여러 목적을 담으면 롤백·히스토리 확인이 어렵습니다.

```bash
git add {로그인 페이지 추가에 관한 파일}
git commit -m "feat: 로그인 페이지 추가"

git add {로그인 페이지 오류 수정에 관한 파일}
git commit -m "fix: 로그인 페이지 오류 수정"
```

---

## 3. 이슈 관리

JIRA 대신 **GitHub Issues** 를 씁니다. 작업 시작 전에 이슈를 먼저 만들고, 이슈 번호로 브랜치와 PR을 연결합니다.

레포의 `.github/ISSUE_TEMPLATE/` 에 아래 4종이 등록되어 있습니다. New issue 를 누르면 골라서 쓸 수 있습니다.

### 3-1. ✨ 기능 추가 (`feat`)

```markdown
## ✨ 기능 설명

## 📍 담당 영역
- [ ] 모바일 (apps/mobile)
- [ ] API (apps/api)
- [ ] 공통 (packages, infra, docs)

## 📌 작업 내용
- [ ]
- [ ]
- [ ]

## 🎯 기대 효과

## 🌿 작업 브랜치
`work/<이름>/feat/<short-description>`

## ⚠️ 공통 파일 변경 여부
- [ ] src/theme/, src/components/
- [ ] app/_layout.tsx, app/(tabs)/_layout.tsx
- [ ] app.config.ts, package.json, package-lock.json
- [ ] .gitignore, .env.example
- [ ] 새 라이브러리 설치 / 환경변수 추가
- [ ] 해당 없음

## 📎 참고 자료
```

### 3-2. 🐛 버그 리포트 (`fix`)

```markdown
## 🐛 버그 설명

## 📍 발생 위치

## 💻 실행 환경
- [ ] iOS 시뮬레이터 (Expo Go)
- [ ] Android
- [ ] 웹 (w)
- [ ] 백엔드 / Docker

## 🔄 재현 방법
1.
2.
3.

## ✅ 기대 동작

## 📸 참고 자료
```

### 3-3. 🛠 설정·환경 (`chore`)

```markdown
## 🛠 작업 내용
- [ ]
- [ ]
- [ ]

## 📌 상세 설명

## 📦 라이브러리를 설치한다면
| 항목 | 내용 |
| --- | --- |
| 패키지명 / 버전 | |
| peer dependency | |
| Expo SDK 57 · RN 0.86 호환 | |
| 웹 지원 여부 | |

## 🔍 참고 사항
```

### 3-4. 📝 문서 (`docs`)

```markdown
## 📝 문서 작업 내용
- [ ]
- [ ]

## 📂 대상 문서

## 📌 상세 설명

## 📎 참고 자료
```

### 라벨 만들기

템플릿이 붙이는 라벨은 **레포에 이미 존재하는 라벨만** 적용됩니다. Issues → Labels 에서 아래 4개를 먼저 만들어주세요.

| 라벨 | 색상 추천 |
| --- | --- |
| `feat` | `#FF7A45` (귤) |
| `fix` | `#D73A4A` |
| `chore` | `#7A7A7A` |
| `docs` | `#2BB8AC` (에메랄드) |

---

## 4. PR 템플릿

`.github/pull_request_template.md` 에 등록되어 있어 PR을 열면 자동으로 채워집니다.
제목은 대표 커밋 메시지와 동일하게 (`feat: 내 여행 지도 탭 추가`).

```markdown
## 작업 내용
-

## 변경 사항
-

## 확인 사항
- [ ] base 브랜치가 올바릅니다. (작업 브랜치 → dev/<이름>-main, 개인 통합 → main)
- [ ] 커밋 메시지가 `<type>: <내용>` 형식이고, 커밋당 목적이 하나입니다.
- [ ] npm run lint / npm run typecheck 를 통과했습니다. (백엔드는 ruff check / pytest)
- [ ] 화면 또는 API 동작을 직접 확인했습니다.
- [ ] 충돌이 없습니다.

## 공통 파일 변경
- [ ] src/theme/, src/components/
- [ ] app/_layout.tsx, app/(tabs)/_layout.tsx
- [ ] app.config.ts, package.json, package-lock.json
- [ ] .gitignore, .env.example
- [ ] 새 라이브러리 설치 / 환경변수 추가 / 네이티브 권한 추가
- [ ] 해당 없음

## 관련 이슈
close #
```

> **base 브랜치 주의** — GitHub 기본값이 `main` 이라 실수하기 쉽습니다.
> 잘못 열었으면 닫지 말고 Edit → base 변경 → Change base 로 고치면 됩니다.

---

## 5. main 브랜치 보호 — 승인 1명 필수

**레포 소유자(Gayoung03) 또는 Admin 권한이 있는 사람만** 설정할 수 있습니다.
Public 레포이므로 무료 플랜에서도 사용 가능합니다.

### 방법 A. Rulesets (현재 GitHub 권장)

1. 레포 → **Settings** → 왼쪽 **Rules** → **Rulesets** → **New ruleset** → **New branch ruleset**
2. **Ruleset Name**: `main protection`
3. **Enforcement status**: `Active`
4. **Target branches** → Add target → **Include default branch** (= `main`)
5. **Rules** 에서 체크:
   - ✅ **Require a pull request before merging**
     - **Required approvals**: `1`
     - ✅ Dismiss stale pull request approvals when new commits are pushed (새 커밋이 올라오면 기존 승인 무효화)
     - ✅ Require conversation resolution before merging (리뷰 코멘트 해결 후 머지)
   - ✅ **Require status checks to pass** → `Mobile CI` / `API CI` 추가 (선택, 권장)
   - ✅ **Block force pushes**
6. **Create** 클릭

### 방법 B. Branch protection rules (기존 방식)

1. 레포 → **Settings** → **Branches** → **Add branch protection rule** (또는 Add classic branch protection rule)
2. **Branch name pattern**: `main`
3. ✅ **Require a pull request before merging**
   - ✅ **Require approvals** → 개수 `1`
   - ✅ Dismiss stale pull request approvals when new commits are pushed
4. ✅ Require status checks to pass before merging → `Mobile CI`, `API CI` (선택)
5. ✅ Require conversation resolution before merging (선택)
6. **Create** / **Save changes**

### 설정 후 달라지는 것

- `main` 으로 가는 PR은 팀원 **1명이 Approve 해야** Merge 버튼이 활성화됩니다.
- **본인 PR은 본인이 승인할 수 없습니다.** 반드시 다른 팀원에게 리뷰를 요청하세요.
- `main` 직접 push 가 막힙니다.
- 개인 통합 브랜치(`dev/*`)는 보호 대상이 아니므로 1단계 PR은 지금처럼 혼자 머지하면 됩니다.

### 팀원이 모두 승인 권한을 가지려면

Settings → **Collaborators and teams** 에서 팀원 권한이 **Write** 이상이어야 리뷰 승인이 유효합니다.
(Read 권한은 승인해도 Required approval 로 집계되지 않습니다.)

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-07 | 이슈 템플릿 4종 추가, PR 템플릿 보강, main 브랜치 보호 규칙 문서화 |

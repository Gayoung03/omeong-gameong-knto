# Branch & PR Rules

## 1. Branch Strategy

이 프로젝트는 `main` 브랜치를 최종 안정 브랜치로 유지한다.

모든 팀원은 `main`에서 개인 통합 브랜치를 만들고, 실제 작업은 개인 통합 브랜치에서 다시 작업 브랜치를 만들어 진행한다.

병합 흐름은 다음 순서를 따른다.

```text
main
-> dev/<name>-main
-> work/<name>/<type>/<short-description>
-> dev/<name>-main
-> main
```

## 2. Required Start Flow

작업을 시작하기 전에는 반드시 개인 통합 브랜치에서 최신 `main` 내용을 먼저 확인하고 반영한다.

기본 순서는 다음과 같다.

```bash
git switch dev/<name>-main
git fetch origin main
git merge origin/main
git switch -c work/<name>/<type>/<short-description>
```

`git fetch origin main`은 원격 `main`의 최신 변경사항을 가져오는 명령이다.

`fetch`만으로는 현재 브랜치에 변경사항이 반영되지 않으므로, 개인 통합 브랜치에서 `git merge origin/main`까지 진행한 뒤 작업 브랜치를 만든다.

개인 통합 브랜치가 아직 없다면, 최신 `main`에서 먼저 개인 통합 브랜치를 만든다.

```bash
git switch main
git fetch origin main
git pull origin main
git switch -c dev/<name>-main
git push -u origin dev/<name>-main
```

## 3. Branch Naming Rules

### 개인 통합 브랜치

형식:

```text
dev/<name>-main
```

예시:

```text
dev/gayoung-main
dev/minsu-main
dev/jiyoon-main
dev/hyunwoo-main
```

### 작업 브랜치

형식:

```text
work/<name>/<type>/<short-description>
```

예시:

```text
work/gayoung/docs/branch-pr-rules
work/minsu/feat/login-page
work/jiyoon/fix/map-marker-error
work/hyunwoo/refactor/api-client
```

### Branch Type

| Type | 의미 |
| --- | --- |
| `feat` | 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 변경 |
| `refactor` | 코드 구조 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 설정, 빌드, 기타 작업 |

## 4. Branch Rules

- `main`에는 직접 push하지 않는다.
- 모든 작업은 작업 브랜치에서 진행한다.
- 작업 브랜치는 반드시 개인 통합 브랜치에서 생성한다.
- 작업 브랜치를 만들기 전 개인 통합 브랜치에서 최신 `main`을 fetch하고 merge한다.
- 작업 완료 후 작업 브랜치를 개인 통합 브랜치로 먼저 병합한다.
- 개인 통합 브랜치에서 충돌, 실행 오류, 테스트 문제를 확인한 뒤 `main`으로 병합한다.
- 브랜치 이름에는 작업자를 구분할 수 있도록 `<name>`을 포함한다.
- `<name>`은 GitHub ID 또는 팀에서 정한 영문 닉네임을 사용한다.

## 5. PR Rules

PR은 다음 두 단계로 생성한다.

1. 작업 브랜치 -> 개인 통합 브랜치
2. 개인 통합 브랜치 -> `main`

### PR Title

PR 제목은 다음 형식을 사용한다.

```text
<type>: <작업 요약>
```

예시:

```text
docs: 브랜치 및 PR 규칙 추가
feat: 로그인 페이지 추가
fix: 지도 마커 표시 오류 수정
```

## 6. PR Template

```md
## 작업 내용

-

## 변경 사항

-

## 확인 사항

- [ ] 대상 브랜치가 올바른지 확인했습니다.
- [ ] 충돌이 없는지 확인했습니다.
- [ ] 실행 또는 테스트를 확인했습니다.

## 관련 이슈

close #
```

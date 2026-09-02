# AI 입출력 개편 잔여 작업 구현 계획 (v2 — 리뷰 반영)

> 2026-09-02. `docs/api/ai-io-column-design.md`(7장·8.1·8.3)에서 확정됐으나 미구현으로 실측된
> 항목들의 구현 계획. v1 → 4-관점 리뷰 패널(database·fastapi·security·architect, 지적 33건 중
> 32건 유효) 반영해 v2. 진행: 구현 → 코드 리뷰 → `make check` → (사용자 승인 후) 커밋·PR.

## 0. 범위

| # | 항목 | 원본 | 상태 근거 |
|---|---|---|---|
| C1 | 챗봇 title 서버 생성 (첫 질문 30자 문장 경계 절단) | 7.6·8.4 | 코드 미구현 + chatbot.md의 "미구현" 노트 갱신 필요 |
| C2 | 탈퇴 시 chat_conversations 하드 삭제 | 8.3-2 확정 | DELETE /users/me 는 deleted_at만 기록 |
| C3 | request_text LLM 구조화 추출 → 추천 생성에 반영 | 7.7·8.3-3 | write-only. **pace 병합은 제외**(아래) |
| C4 | 가이드 body ↔ 규정 테이블 정합 검사 + body 1,200자 가드 | 7.5 | 테스트 부재. 1,200자 적재 계약도 미구현 |
| D1 | `places.business_hours_raw` 이관 (추출→기존 apply 재사용) | 7.3·8.1 | 0/1,299. **실DB 적용은 8.1 ①② 이후** |
| D2 | `places.category_detail` 적재 (etc 278건) | 7.2 | 0건. 리허설 실측: KCISA 템플릿으로 4분류 결정적 추출 |
| D3 | `transport_restricted_breeds` 적재 + `source_url` 백필 + **응답 노출** | 7.4 | 0행·0/12. 읽는 코드가 없으면 "죽은 데이터"라 노출까지 |
| D4 | 파싱 배치가 채운 행의 `reliability_score`·`verified_at` 소급 백필 | 7.1 "파싱 배치에서 채움" | 컬럼·응답 노출은 있는데 배치가 안 채움 (리뷰 발견) |
| Doc1 | 좌표 예외 명문화 + README 8장에 OpenAI 해외 전송 고지 항목 | 8.3-1·8.2-4 | 미반영 |
| Doc2 | 운송규정 API `cabinWeightUnlimited`·`cargoWeightUnlimited`·`cabinConditions` 노출 | 8.1 | 스키마·명세·**조립 생성자** 모두 누락 |

이행 확인돼 범위에서 뺀 것: 시드 좌표 채우기(7.7 — seed_dev 4곳 전부 좌표 보유),
`_verdict` unlimited 연쇄(8.1 — #199 반영), 아시아나 16주(실서버 실측 16).

**명시적 제외**: ① raw_text DROP — 8.1 순서(①places.md 계약 갱신+프론트 조율 → ②응답 참조
제거 배포 → ③이관 검증 → ④DROP) 중 ①이 프론트 조율. **D1 실DB 적용도 ①② 뒤로 보류**
(리뷰 지적: 먼저 채우면 이중 진실원본 기간만 늘어남) — 이번엔 스크립트+테스트+리허설 검증까지.
② C3의 pace·applied_weights 병합 — pace 는 "기본값" 상태가 스키마에 없어 명시 선택과 구분
불가(검증됨), weights 는 추출 스키마 밖. **preferred_tags 만 병합** (8.3-3 취지 유지, 리뷰 확정).

## 1. 브랜치·PR (git-convention: 이슈 선생성, work→dev→main 2단계, 한 커밋=한 목적)

| PR | 브랜치 | 내용 |
|---|---|---|
| D | `work/viowlet/feat/guides-rule-fields` | Doc2 + C4 + 가이드 시드 데이터 보완(에어부산 문구 등 7.5 잔여) |
| A | `work/viowlet/feat/chat-lifecycle` | C1 + C2 (+ users.md·chatbot.md 갱신) |
| C | `work/viowlet/feat/design-backlog-batches` | D1 + D2 + D4 + Doc1 |
| B | `work/viowlet/feat/request-text-extract` | C3 (+ §2.7 PII 표 갱신) |
| E | `work/viowlet/feat/restricted-breeds` | D3 (유니크 제약 소마이그레이션 + 리서치 + 시드 반영 + 노출) |

순서 **D → A → C → B → E**. 7.5 "가이드 보완+견종 묶음"은 D(시드 보완)·E(견종)로 나누되
C4 커버리지 목록이 E에서 breeds 추가 시 함께 갱신되도록 커버리지 검사로 강제(아래 C4).

## 2. 항목별 설계 (v2 변경점 굵게)

### C1 — 챗봇 title 서버 생성 (PR A)
- 구현: `create_message` 질문 커밋 전, `title IS NULL AND 기존 메시지 0건`이면
  `conversation.title = derive_title(content)` 같은 트랜잭션 커밋 (8.4: SSE start=질문 커밋 시점).
- `derive_title(text, 30)` 순수 함수: 공백 정규화 → 30자 이내 마지막 문장 경계(`.?!…` 공백) 절단
  → 없으면 하드 컷 → 빈 결과면 `"새 대화"`.
- **문서: chatbot.md의 "title 생성은 firstMessage와 같은 시점(미구현)" 노트를 실제 동작
  (messages 첫 질문 시 생성, firstMessage 는 여전히 미구현)으로 갱신** (리뷰: "문서 변경 없음"은 오류).
- **동시성 문구 정정**: 동시 첫 질문 2건이면 나중 커밋이 이김 — 값이 다를 수 있으나 title 은
  사용자 수정 가능(PATCH)한 표시용 문자열이라 실해 미미. 잠금 없음(KISS).
- 테스트: 절단 단위 6케이스 + 통합 3(생성/지정 시 불변/두 번째 질문 불변).

### C2 — 탈퇴 시 chat 하드 삭제 (PR A)
- **문서 먼저**: users.md DELETE /users/me — "탈퇴 시 챗봇 대화·메시지 즉시 물리 삭제(복구 불가)"
  + 변경 이력. 근거: 8.3-2 FK 전수 검증(연쇄는 chat_messages 뿐).
- 구현: `delete_me`에서 deleted_at 기록과 같은 트랜잭션으로
  `DELETE FROM chat_conversations WHERE user_id=:id` (명시 쿼리 — relationship 금지 컨벤션).
- **각주(리뷰)**: `notifications.target_id`(FK 없는 앱 레벨 참조)에 삭제된 대화 id 가 남을 수 있음
  — 탈퇴 사용자는 알림 조회 불가라 실해 없음, 회원 물리 삭제 시 user FK CASCADE 로 정리됨. 테스트로 고정.
- 테스트: 통합 — 탈퇴 후 chat 0건·타 도메인 무사·404 규칙 불변.

### C3 — request_text 구조화 추출 (PR B)
- **문서 먼저**: routes.md 에 동작(202 불변, 백그라운드 추출, 실패 무시) +
  **ai-io-column-design §2.7 PII 표에 `route_requests.request_text = 상(잠재)` 행 추가**(8.1 이행).
- `app/integrations/llm/request_intent.py` — route_edit 미러 + **강화**:
  OpenAI tool 강제 + **`strict: true`** + 응답 후 **서버측 재검증**(`STANDARD_TAG_SET` 교집합 필터 —
  strict 미보장 모델·값 오염 이중 방어). 출력: `preferred_tags`만. 자유 문자열 필드 없음.
  원문 로그 금지(길이만). 설정: `request_intent_model`·`request_intent_timeout_seconds`
  (기본 route_edit 값과 동일 — 신규 env 불필요).
- **병합 방식(리뷰 3건 반영)**: `generate_route` 초입에서
  `merged_tags = merge_preferred_tags(request.preferred_tags, extracted)` **로컬 변수**로 만들고,
  함수 내 `request.preferred_tags` **사용처 3곳(ScoringContext·restaurant_preferred·저녁 검증)을
  전부 `merged_tags` 로 치환** — request ORM 인스턴스는 절대 변경하지 않음(말미 커밋에 딸려
  영속화되는 사고 차단). 추출 호출은 **TourAPI 와 동일한 try/except 로 실패 무시** 명문화.
- 테스트: merge 순수 함수 단위 + strict 스키마·재검증 단위(모킹) + "추출 실패에도 생성 진행" 통합.

### C4 — 정합 검사 + 1,200자 가드 (PR D)
- **재설계(리뷰 2건)**: DB 통합 테스트가 아니라 **seed_guides.py 의 정의(dict·body 문자열)를
  직접 import 해 대조하는 순수 테스트** — 실행 환경 데이터에 무관·결정적.
  1. 규정 dict 의 수치 컬럼(kg·주·원·시간)이 **해당 문서 body 에 다른 수치로 단정 표기되지
     않는지** 검사: body 에서 `숫자+단위` 패턴을 추출해 같은 단위의 규정값과 대조(불일치=실패,
     body 미등장=통과).
  2. **커버리지 강제**: 검사한 (slug, 컬럼) 집합이 규정 dict 의 수치 필드 전체와 일치해야 함 —
     규정 추가 시 테스트 갱신을 컴파일 타임처럼 강제.
  3. **body ≤ 1,200자** 전 문서 검사 + `seed_guides.py` 적재 함수에 초과 시 예외(적재 거부) 추가.
- 가이드 시드 보완(7.5 잔여): 에어부산 당일신청 단정 문구·prep-rental-car 출처·자기참조 출처
  2건 — seed_guides 내용 검토 후 미반영분만 수정.

### D1 — business_hours_raw 이관 (PR C)
- **아키텍처 변경(리뷰 HIGH 2건)**: 직접 UPDATE 스크립트가 아니라
  `scripts/extract_business_hours_raw.py` 는 **추출만**: place_id 그룹핑,
  `notes_parsing.normalize_bar` 정규화, `COUNT(DISTINCT)>1` → review_queue(리허설 실측 0건 —
  안전장치), 단일값 장소만 제안 생성. 산출은 **기존 스테이징 스키마**
  (`table:"places", column:"business_hours_raw", reliability:100, method:"regex:hours-raw"`)로
  **전용 파일** `infra/batch/business_hours_raw_staging.json` (파싱 배치 검수 흐름과 분리).
  **반영은 `apply_place_batch --in <파일>` 재사용** — 화이트리스트·IS NULL 가드·dry-run 상속.
- 소스는 드롭 전 원본 `place_business_hours.raw_text` 명시(8.1). **실DB 적용은 8.1 ①② 뒤**.
- 테스트: 그룹핑·정규화·큐 판정 단위.

### D2 — category_detail 적재 (PR C)
- 같은 구조: `scripts/extract_category_detail.py` 추출만 → 전용 스테이징
  `infra/batch/category_detail_staging.json` → **apply_place_batch 재사용**(리뷰: 반영 경로 공백 해소).
- 규칙: description 의 `[KCISA 원본 분류] … > 말단` 추출(리허설 실측: 동물약국 126·동물병원 75·
  반려동물용품 51·미용 26 = 278 전량). 말단 없으면 review 로.
- **값 규약 확정(리뷰 HIGH)**: **KCISA 말단 분류 한글 원문 그대로** — places.md 기존 계약
  "예: etc 안의 동물약국·동물병원, 라벨 표기는 앱"과 일치. enum 아님(코드화하지 않음). 계약 변경 없음.

### D4 — reliability·verified_at 소급 백필 (PR C, 신규)
- `scripts/backfill_policy_reliability.py`: 파싱 배치가 채운 `place_pet_policies` 행
  (caution_note 등 대상 컬럼이 NOT NULL 이고 `reliability_score IS NULL`)에
  `reliability_score`(정규식분 100·LLM분 70 — 스테이징 JSON 의 pk·reliability 를 입력으로)와
  `verified_at`(배치 실행일) 기록. dry-run·멱등·IS NULL 가드.
- 입력: 오늘 반영에 쓴 검수본 스테이징 JSON 2개(로컬 보존分). 향후 배치부터는
  apply_place_batch 가 값 반영 시 함께 기록하도록 **apply 확장**(같은 PR, 별 커밋).

### D3 — restricted_breeds (PR E)
- **소마이그레이션**: `(transport_pet_rule_id, breed_name_ko)` UniqueConstraint —
  DB 최종 방어선(리뷰). **스키마 변경이므로 dbml·table-reference 동시 갱신 + migration-smoke**.
- 리서치: 공식 도메인 화이트리스트(koreanair.com·flyasiana.com·airbusan.com·jinair.com·
  jejuair.net·eastarjet.com·twayair.com + 선사 공식) **밖 출처는 적재 금지**. 근거 원문 인용.
- 적재: `scripts/seed_restricted_breeds.py` — 대상 규정 행은 **(carrier_name, route) 튜플**로
  특정(여객선 다중 행 대응). source_url 백필 동봉(IS NULL 가드).
- **시드 일관성(리뷰)**: 확정값(unlimited·conditions·breeds·source_url)을 `seed_guides.py`
  원본에도 반영 — 재시드·리허설 환경이 백필 없이도 같은 상태가 되게.
- **소비자(리뷰 HIGH "죽은 데이터")**: guides.md 명세 갱신 후 운송규정 응답에
  `restrictedBreeds: [{breedNameKo, cabinBlocked, cargoBlocked, note}]` 노출 + C4 커버리지 갱신.

### Doc1 — 문서 (PR C)
- CLAUDE.md GPS 항목에 예외: "단말 GPS 금지. 주소·장소명 유도 지오코딩 좌표는 예외(8.3-1,
  2026-08-31 팀 결정)". `docs/database/README.md` 동일 취지.
- `docs/api/README.md` 8장 미정 목록에 "OpenAI 해외 전송 제3자 고지(출시 전, 개인정보처리방침)" 추가.

### Doc2 — 운송규정 필드 노출 (PR D)
- guides.md 필드 표에 3필드 + **3값 의미 전부**: `true`=무제한(무게 상한 없음) /
  `false`=무제한 아님(상한 존재 또는 불허) / `null`=미확인. 변경 이력 + PR 에서 yulim 공유.
- 구현: `TransportRuleResponse` 3필드 + **`_transport_rule_response` 생성자에 매핑 추가**
  (리뷰: model_validate 아님) + 목록·상세 두 경로 테스트.

## 3. 게이트·컨벤션 (전 PR 공통)
1. 팀 컨벤션 준수: 작업 전 이슈 생성(`close #`), dev 최신화 후 work 분기, `<type>: 한글 요약`
   한 커밋=한 목적, **문서(명세) 커밋이 코드 커밋 선행**, 응답 camelCase=DB 컬럼명, 패키지 추가 없음,
   sync SQLAlchemy·레이어·`uv run`, lockfile 불변.
2. PR 단위 `make check`. DB 스키마 변경은 E 의 유니크 제약 1건뿐 — dbml·reference·smoke 동반.
3. 코드 리뷰: code-reviewer + python/fastapi/database-reviewer, A·B 는 security-reviewer 추가.
4. 배치 실행은 리허설 실측 → 사용자와 `!`/railway ssh 로 RDS·Railway 순 적용(금일 확립 절차).
   **D1 실적용 제외**(8.1 순서 보류), D2·D4 는 적용 대상.
5. 커밋·push·이슈 생성은 사용자 승인 후 일괄.

## 4. 리스크
- C2 비가역 삭제 — 명세 선행·테스트로 범위 고정. C3 OpenAI 실호출 — 짧은 타임아웃·실패 무시·
  기존 추천 테스트 전체 회귀. D3 리서치 — 공식 출처 미확보 운송사는 미적재(과보정 금지)·보고.
- 브랜치 간 파일 충돌: A(chatbot.py)·B(route_recommendation.py)·C(scripts)·D(guides)·E(guides+모델)
  — D 와 E 가 guides 를 공유하므로 **E 는 D 머지 후 분기**.

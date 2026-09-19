/**
 * 항공사·여객선 공식 안내 페이지 주소 (앱 내장).
 *
 * 운영 DB 의 `guide_document_sources.source_url` 이 비어 있어 앱이 직접 들고 있는다.
 * 항공사 7곳은 `apps/api/scripts/seed_guides.py` 의 GUIDE_DOCUMENTS 와 같다 — 주소를 바꿀 때는 두 곳을 함께 고친다.
 * 여객선 3곳은 앱에만 있다 (시드에는 아직 None).
 * API 가 주소를 내려주면 그쪽이 우선이고, 이 표는 비어 있을 때만 쓰인다 (`guidesApi.ts` 의 `resolveOfficialSource`).
 *
 * 아리온제주는 홈페이지에 반려동물 안내가 없어 넣지 않았다 — 없으면 화면이 링크 버튼을 그리지 않는다.
 */
export type OfficialSource = {
  url: string;
  /** 링크를 눌렀을 때 헷갈릴 수 있는 점. 화면에 작게 보인다 */
  hint?: string;
};

export const OFFICIAL_SOURCES: Record<string, OfficialSource> = {
  'airline-korean-air': {
    url: 'https://www.koreanair.com/contents/plan-your-travel/special-assistance/travel-with-pets/guide',
  },
  'airline-asiana': {
    url: 'https://flyasiana.com/C/KR/KO/contents/traveling-with-pets',
  },
  'airline-jeju-air': {
    url: 'https://www.jejuair.net/ko/linkService/help/main.do',
    hint: '「도움이 필요한 고객」 페이지에서 반려동물 항목을 찾아 주세요.',
  },
  'airline-tway': {
    url: 'https://www.twayair.com/app/serviceInfo/contents/1070',
    hint: '사명 변경으로 트리니티항공 홈페이지로 연결됩니다.',
  },
  'airline-jin-air': {
    url: 'https://www.jinair.com/addService/jinipet/statute',
  },
  'airline-air-busan': {
    url: 'https://www.airbusan.com/content/common/service/customer/animal',
  },
  'airline-eastar-jet': {
    url: 'https://www.eastarjet.com/newstar/PGWIM00004',
  },
  'ferry-hanil-wando': {
    url: 'https://www.hanilexpress.co.kr/event/specialServiceDtl.do',
  },
  // 목포·진도 두 항로가 같은 문서를 쓴다
  'ferry-seaworld-mokpo-jindo': {
    url: 'https://seaferry.co.kr/bbs/content.php?co_id=p201&tab=pet',
  },
  'ferry-oceanvista-samcheonpo': {
    url: 'https://www.oceanvista.co.kr/theme/main/html/board_process.detail.php',
  },
};

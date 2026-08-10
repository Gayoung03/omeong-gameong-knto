/**
 * 색상 토큰 정본.
 *
 * 규칙
 * - 화면·컴포넌트에서 hex 리터럴을 직접 쓰지 않는다. 반드시 이 파일의 토큰을 참조한다.
 * - 새 색이 필요하면 여기에 토큰을 추가한 뒤 참조한다. 화면 파일에서 즉석으로 만들지 않는다.
 * - 예외는 파일 하단 `brandColors`(외부 브랜드 규정값)뿐이다.
 *
 * 팔레트 근거: 시안 키 컬러 — 귤(primary) / 귤나무 잎(leaf) / 에메랄드 바닷빛(sea) / 현무암(basalt)
 */
export const colors = {
  /** 시안 키 컬러(귤). 통합 시 `#FF7A45` 로 확정했다. */
  primary: '#FF7A45',
  /** 버튼 눌림·강조 텍스트 등 primary 보다 진한 톤 */
  primaryDeep: '#B05A2A',
  /** 연한 주황 배경 위에 얹는 진한 갈색 텍스트 */
  primaryInk: '#5A3220',
  /** 아주 연한 주황 배경 (배지·카드) */
  primarySoft: '#FFF1E8',
  /** primarySoft 보다 한 단계 진한 주황 배경 (선택 상태·강조 배지) */
  primarySoftStrong: '#FFE2C4',

  secondary: '#4CAF88',

  background: '#FFFFFF',
  surface: '#FFFFFF',

  /** 본문 텍스트 */
  textPrimary: '#333333',
  /** textPrimary 와 basalt 사이의 진한 회갈색. 소제목·강조 라벨 */
  textStrong: '#514C48',
  /** 보조 텍스트 */
  textSecondary: '#7A7A7A',
  /** placeholder·비활성 텍스트 */
  textTertiary: '#A8A49B',

  border: '#EEEEEA',
  divider: '#E5E5E5',
  iconGray: '#7E8582',
  neutralGray: '#F5F6F4',

  success: '#2EAF6D',
  warning: '#F5A623',
  error: '#E5484D',
  errorBg: '#FDECEC',

  /** 달력 주말 표기 (일=빨강, 토=파랑 관행) */
  calendarSunday: '#E5484D',
  calendarSaturday: '#3E6FB8',

  /** 귤나무 잎 */
  leaf: '#4E7A3A',
  leafSoft: '#EAF3E2',

  /** 에메랄드 바닷빛 */
  sea: '#2BB8AC',
  /** sea 보다 진한 톤. 아이콘·강조 텍스트 */
  seaDeep: '#188F7B',
  /** 연한 바닷빛 배경 */
  seaSoft: '#E0F5F2',
  /** seaSoft 보다 더 연한 배경 */
  seaSoftLight: '#EEF8F5',

  /** 현무암 */
  basalt: '#33302C',
  basaltSoft: '#F1EFEA',
} as const;

/**
 * 카테고리·썸네일처럼 "데이터로서의 색".
 * 브랜드 팔레트와 섞지 않는다. 서버가 색을 내려주기 시작하면 이 목록이 매핑 기준이 된다.
 */
export const categoryColors = {
  green: { fg: '#188F7B', bg: '#E4F7F2' },
  orange: { fg: '#C85F00', bg: '#FFF0E9' },
  yellow: { fg: '#B7841A', bg: '#FFF7DC' },
  blue: { fg: '#3E6FB8', bg: '#E4EDF9' },
  purple: { fg: '#6B5FA8', bg: '#E6E1F8' },
  leaf: { fg: '#4E7A3A', bg: '#E9F1DC' },
} as const;

export type CategoryColorName = keyof typeof categoryColors;

/** 목록 썸네일 배경처럼 순서대로 돌려 쓰는 파스텔 배경 */
export const thumbnailPalette = [
  categoryColors.green.bg,
  categoryColors.orange.bg,
  categoryColors.yellow.bg,
  categoryColors.blue.bg,
  categoryColors.purple.bg,
  categoryColors.leaf.bg,
] as const;

/**
 * 외부 서비스 브랜드 규정값. **변경 금지.**
 * 각 사의 브랜드 가이드라인에 정해진 색이라 theme 토큰으로 치환하면 안 된다.
 */
export const brandColors = {
  naver: { background: '#03C75A', text: '#FFFFFF' },
  kakao: { background: '#FEE500', text: '#191919' },
  google: { background: '#FFFFFF', text: '#4285F4' },
} as const;

/**
 * 오버레이·그림자처럼 투명도가 필요한 색.
 * rgba 리터럴을 화면 파일에 흩뿌리지 않기 위해 여기로 모은다.
 */
export const overlayColors = {
  /** 바텀시트·모달 뒤 배경 */
  scrim: 'rgba(30, 28, 25, 0.45)',
  /** 이미지 위 딤 처리 */
  dim: 'rgba(0, 0, 0, 0.48)',
  /** 사진 전체보기처럼 거의 불투명한 어두운 배경 */
  photoViewer: 'rgba(30, 28, 25, 0.92)',
  /** 지도·이미지 위에 얹는 반투명 흰 카드 */
  frostedCard: 'rgba(255, 255, 255, 0.94)',
  /** 이미지 위 옅은 흰 배지 */
  whiteVeil: 'rgba(255, 255, 255, 0.17)',
  /** 어두운 배경 위 흰 텍스트 */
  onDarkText: 'rgba(255, 255, 255, 0.85)',
  /** 이미지 위 텍스트 그림자 */
  textShadow: 'rgba(0, 0, 0, 0.28)',
  /** primary 를 옅게 깐 테두리 */
  primaryBorder: 'rgba(255, 122, 69, 0.22)',
  /** 그림자 기준색 */
  shadow: '#000000',
} as const;

export const colors = {
  /**
   * 통합 시 primary 는 `#FF7A45` 로 확정했다.
   * 프로젝트 스캐폴드의 원래 값이자 시안 키 컬러(귤)이며, theme 토큰으로 가장 널리 쓰인다.
   */
  primary: '#FF7A45',
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
  /** 경고 아이콘·배지 배경으로 쓰는 연한 코랄 */
  errorBg: '#FDECEC',

  /** 화면 시안의 키 컬러(귤·귤나무 잎·에메랄드 바닷빛·현무암) 기반 확장 토큰 */
  primarySoft: '#FFF1E8',
  leaf: '#4E7A3A',
  leafSoft: '#EAF3E2',
  sea: '#2BB8AC',
  seaSoft: '#E0F5F2',
  basalt: '#33302C',
  basaltSoft: '#F1EFEA',

  /** 역할 기반 토큰 */
  mintBg: '#EEF8F5',
  mintIcon: '#52B9A5',
  orangeBg: '#FFF3EA',
  orangeIcon: '#FF8A4C',
  iconGray: '#7E8582',
  neutralGray: '#F5F6F4',
} as const;

/**
 * TODO(디자인 통일): 위 두 묶음은 사실상 같은 팔레트를 다른 이름으로 쓰고 있다.
 *   primarySoft ↔ orangeBg / sea ↔ mintIcon / seaSoft ↔ mintBg / primary ↔ orangeIcon
 * 통합 중에는 양쪽 화면이 모두 깨지지 않도록 일부러 둘 다 남겨두었다.
 * 토큰 확정 단계에서 하나로 합치고 사용처를 일괄 치환할 것.
 */

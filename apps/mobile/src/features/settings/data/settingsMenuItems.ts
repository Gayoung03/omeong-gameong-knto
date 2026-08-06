import type { Href } from 'expo-router';

/** 화면 이동이 아니라 설정 화면 안에서 처리해야 하는 동작 */
export type SettingsMenuAction = 'logout';

export type SettingsMenuItem = {
  label: string;
  trailingText?: string;
  /** 값이 있으면 SettingsScreen이 이 경로로 이동시킨다. */
  route?: Href;
  /** 값이 있으면 SettingsScreen이 해당 동작을 실행한다. route와 함께 쓰지 않는다. */
  action?: SettingsMenuAction;
};

export const settingsMenuItems: SettingsMenuItem[] = [
  { label: '공지사항', route: '/notices' },
  { label: '알림설정', route: '/notification-settings' },
  { label: '버전정보', trailingText: '현재 1.82.0' },
  // TODO: 이용약관 화면 연결
  { label: '이용약관' },
  // TODO: 개인정보 취급방침 화면 연결
  { label: '개인정보 취급방침' },
  { label: '탈퇴하기', route: '/account-withdraw' },
  { label: '로그아웃', action: 'logout' },
];

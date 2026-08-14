import {
  getAuthSession,
  updateSessionNickname,
} from '@/src/features/auth/services/authStorage';
import type { User } from '@/src/types/user';

const UPLOAD_DELAY_MS = 400;
const UPDATE_DELAY_MS = 300;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 로그인한 사용자 정보. 아직 사용자 API가 없어 메모리에만 들고 있다.
 *
 * 이메일·닉네임은 로그인·회원가입 때 저장한 세션에서 가져오고,
 * 프로필 이미지처럼 세션에 없는 값은 목업으로 남긴다.
 * TODO: 사용자 API(GET /users/me) 연결 시 이 파일 전체를 실제 호출로 교체한다.
 */
let currentMockUser: User = {
  userId: 'user-1',
  nickname: '여행자',
  email: '',
  profileImage: 'https://placehold.co/200x200',
};

export const DEFAULT_PROFILE_IMAGE = '';

export type UpdateUserProfileInput = {
  nickname: string;
  localProfileImageUri?: string;
  resetProfileImage?: boolean;
};

export async function uploadProfileImage(localUri: string): Promise<string> {
  await wait(UPLOAD_DELAY_MS);
  return localUri;
}

export async function updateUserProfile(input: UpdateUserProfileInput): Promise<User> {
  await wait(UPDATE_DELAY_MS);

  const profileImage = input.resetProfileImage ? DEFAULT_PROFILE_IMAGE : input.localProfileImageUri ?? currentMockUser.profileImage;

  currentMockUser = {
    ...currentMockUser,
    nickname: input.nickname,
    profileImage,
  };

  // 세션에도 반영해야 앱을 다시 켰을 때 수정한 닉네임이 유지된다.
  await updateSessionNickname(input.nickname);

  return { ...currentMockUser };
}

export async function fetchCurrentUser(): Promise<User> {
  const session = await getAuthSession();

  // 로그인한 계정이 바뀌었을 때만 세션 값으로 갈아끼운다.
  // 매번 덮어쓰면 프로필 편집으로 바꾼 닉네임이 새로고침될 때마다 되돌아간다.
  if (session && session.email !== currentMockUser.email) {
    currentMockUser = {
      ...currentMockUser,
      nickname: session.nickname,
      email: session.email,
    };
  }

  return { ...currentMockUser };
}

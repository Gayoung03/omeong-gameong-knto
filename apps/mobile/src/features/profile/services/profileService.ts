import type { User } from '@/src/types/user';

const UPLOAD_DELAY_MS = 400;
const UPDATE_DELAY_MS = 300;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

let currentMockUser: User = {
  userId: 'user-1',
  nickname: '혼디온',
  email: 'daunkim1111@gmail.com',
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

  return { ...currentMockUser };
}

export async function fetchCurrentUser(): Promise<User> {
  return { ...currentMockUser };
}

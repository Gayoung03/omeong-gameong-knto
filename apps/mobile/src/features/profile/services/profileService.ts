import { Asset } from 'expo-asset';

import { updateSessionNickname } from '@/src/features/auth/services/authStorage';
import { apiClient } from '@/src/services/apiClient';
import { uploadImage } from '@/src/services/uploadImage';
import type { User } from '@/src/types/user';

/**
 * 사용자가 사진을 올리기 전에 보여주는 기본 프로필 일러스트.
 * `Image.resolveAssetSource` 는 react-native-web 에 없어 웹에서 깨지므로 `Asset` 을 쓴다.
 */
const DEFAULT_USER_AVATAR = Asset.fromModule(
  require('@/assets/images/profile/default-user.jpg'),
).uri;

/** 프로필 사진을 지웠을 때 되돌아가는 값. */
export const DEFAULT_PROFILE_IMAGE = DEFAULT_USER_AVATAR;

type UserApiResponse = {
  id: string;
  nickname: string;
  email: string | null;
  profileImageUrl: string | null;
  activitySummary: {
    savedPlacesCount: number;
    savedRoutesCount: number;
    travelLogsCount: number;
  };
};

function toUser(response: UserApiResponse): User {
  return {
    userId: response.id,
    nickname: response.nickname,
    email: response.email ?? '',
    profileImage: response.profileImageUrl ?? DEFAULT_PROFILE_IMAGE,
    activitySummary: {
      savedPlacesCount: response.activitySummary.savedPlacesCount,
      savedCoursesCount: response.activitySummary.savedRoutesCount,
      travelLogsCount: response.activitySummary.travelLogsCount,
    },
  };
}

export type UpdateUserProfileInput = {
  nickname: string;
  localProfileImageUri?: string;
  resetProfileImage?: boolean;
};

export async function uploadProfileImage(localUri: string): Promise<string> {
  return uploadImage(localUri, 'profile');
}

export async function updateUserProfile(input: UpdateUserProfileInput): Promise<User> {
  const response = await apiClient.patch<UserApiResponse>('/users/me', {
    nickname: input.nickname,
    ...(input.localProfileImageUri
      ? { profileImageUrl: input.localProfileImageUri }
      : {}),
    ...(input.resetProfileImage ? { profileImageUrl: null } : {}),
  });

  // 세션에도 반영해야 앱을 다시 켰을 때 수정한 닉네임이 유지된다.
  await updateSessionNickname(input.nickname);

  return toUser(response.data);
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await apiClient.get<UserApiResponse>('/users/me');
  return toUser(response.data);
}

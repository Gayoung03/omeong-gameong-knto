import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { User } from '@/src/types/user';
import { updateUserProfile, uploadProfileImage, type UpdateUserProfileInput } from '../services/profileService';
import { userProfileQueryKey } from './useUserProfile';

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: UpdateUserProfileInput): Promise<User> => {
      let imageUrl: string | undefined = input.localProfileImageUri;

      if (input.localProfileImageUri) {
        imageUrl = await uploadProfileImage(input.localProfileImageUri);
      }

      return updateUserProfile({
        nickname: input.nickname,
        localProfileImageUri: imageUrl,
        resetProfileImage: input.resetProfileImage,
      });
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(userProfileQueryKey(), updatedUser);
    },
  });
}

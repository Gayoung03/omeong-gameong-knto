import { useQuery } from '@tanstack/react-query';
import type { User } from '@/src/types/user';
import { fetchCurrentUser } from '../services/profileService';

export function userProfileQueryKey() {
  return ['profile', 'user'] as const;
}

export function useUserProfile() {
  return useQuery<User>({
    queryKey: userProfileQueryKey(),
    queryFn: fetchCurrentUser,
  });
}

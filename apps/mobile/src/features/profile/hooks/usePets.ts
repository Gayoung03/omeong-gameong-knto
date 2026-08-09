import { useQuery } from '@tanstack/react-query';

import type { Pet } from '@/src/types/pet';

import { fetchAllPets, fetchPets } from '../services/petService';

/** 화면 노출용 활성 반려동물 목록 */
export function petsQueryKey() {
  return ['profile', 'pets'] as const;
}

/** 지워진 프로필까지 포함한 전체 목록. 과거 기록의 필터 옵션 등에만 쓴다. */
export function allPetsQueryKey() {
  return ['profile', 'pets', 'all'] as const;
}

export function usePets() {
  return useQuery<Pet[]>({
    queryKey: petsQueryKey(),
    queryFn: fetchPets,
  });
}

export function useAllPets() {
  return useQuery<Pet[]>({
    queryKey: allPetsQueryKey(),
    queryFn: fetchAllPets,
  });
}

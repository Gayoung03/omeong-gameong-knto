import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useLogDraftStore } from '@/src/features/travel-logs/stores/useLogDraftStore';
import type { Pet } from '@/src/types/pet';

import { allPetsQueryKey, petsQueryKey } from './usePets';
import { deletePet } from '../services/petService';

/**
 * 작성 중인 로그 draft에 지워진 반려동물이 선택돼 있으면 그 선택만 걷어낸다.
 * draft의 다른 입력값과 이미 저장된 기록에는 손대지 않는다.
 */
function removePetFromDraft(petId: string) {
  const { draft, updateDraft } = useLogDraftStore.getState();
  if (!draft.petIds.includes(petId)) return;

  updateDraft({ petIds: draft.petIds.filter((id) => id !== petId) });
}

export function useDeletePet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (petId: string): Promise<Pet> => deletePet(petId),
    onSuccess: (deleted) => {
      // 화면에 보이는 활성 목록에서만 제거한다.
      // mock service에는 status: 'deleted'로 남아있고, 여행 로그 캐시는 그대로 둔다.
      queryClient.setQueryData<Pet[]>(petsQueryKey(), (current = []) =>
        current.filter((pet) => pet.petId !== deleted.petId),
      );
      queryClient.invalidateQueries({ queryKey: allPetsQueryKey() });
      removePetFromDraft(deleted.petId);
    },
  });
}

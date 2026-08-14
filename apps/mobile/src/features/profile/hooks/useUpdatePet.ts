import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Pet } from '@/src/types/pet';

import { allPetsQueryKey, petsQueryKey } from './usePets';
import { updatePet, uploadPetImage, type PetFormInput } from '../services/petService';

type UpdatePetVariables = { petId: string; input: PetFormInput };

export function useUpdatePet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ petId, input }: UpdatePetVariables): Promise<Pet> => {
      const uploadedUrl = input.localProfileImageUri
        ? await uploadPetImage(input.localProfileImageUri)
        : undefined;

      return updatePet(petId, { ...input, localProfileImageUri: uploadedUrl });
    },
    onSuccess: (updated) => {
      // 과거 기록은 저장 시점 스냅샷을 보므로 로그 캐시는 건드리지 않는다.
      queryClient.setQueryData<Pet[]>(petsQueryKey(), (current = []) =>
        current.map((pet) => (pet.petId === updated.petId ? updated : pet)),
      );
      queryClient.invalidateQueries({ queryKey: allPetsQueryKey() });
    },
  });
}

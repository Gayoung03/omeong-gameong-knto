import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Pet } from '@/src/types/pet';

import { allPetsQueryKey, petsQueryKey } from './usePets';
import { createPet, uploadPetImage, type PetFormInput } from '../services/petService';

export function useCreatePet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: PetFormInput): Promise<Pet> => {
      // 업로드가 실패하면 등록 자체를 진행하지 않아 사용자가 그대로 재시도할 수 있다.
      const uploadedUrl = input.localProfileImageUri
        ? await uploadPetImage(input.localProfileImageUri)
        : undefined;

      return createPet({ ...input, localProfileImageUri: uploadedUrl });
    },
    onSuccess: (created) => {
      queryClient.setQueryData<Pet[]>(petsQueryKey(), (current = []) => [...current, created]);
      queryClient.invalidateQueries({ queryKey: allPetsQueryKey() });
    },
  });
}

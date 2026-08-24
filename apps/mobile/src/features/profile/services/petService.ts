import { apiClient } from '@/src/services/apiClient';
import { uploadImage } from '@/src/services/uploadImage';
import type { Pet, PetSize, PetSpecies } from '@/src/types/pet';
import type { TravelLogPetSnapshot } from '@/src/types/travelLog';

type PetApiSpecies = 'dog' | 'cat' | 'other';
type PetApiSize = 'small' | 'medium' | 'large';

type PetApiResponse = {
  id: string;
  name: string;
  species: PetApiSpecies;
  speciesDetail: string | null;
  breed: string | null;
  size: PetApiSize | null;
  weightKg: number | null;
  birthDate: string | null;
  age: number | null;
  imageUrl: string | null;
  isPrimary: boolean;
  status: 'active' | 'deleted';
};

type PetListApiResponse = {
  items: PetApiResponse[];
};

const speciesToApi: Record<PetSpecies, PetApiSpecies> = {
  강아지: 'dog',
  고양이: 'cat',
  기타: 'other',
};

const speciesFromApi: Record<PetApiSpecies, PetSpecies> = {
  dog: '강아지',
  cat: '고양이',
  other: '기타',
};

const sizeToApi: Record<PetSize, PetApiSize> = {
  소형: 'small',
  중형: 'medium',
  대형: 'large',
};

const sizeFromApi: Record<PetApiSize, PetSize> = {
  small: '소형',
  medium: '중형',
  large: '대형',
};

export type PetFormInput = {
  name: string;
  species: PetSpecies;
  speciesDetail?: string;
  breed: string;
  birthDate: string;
  weight: number;
  size: PetSize;
  localProfileImageUri?: string;
  removeProfileImage?: boolean;
};

function toPet(response: PetApiResponse): Pet {
  return {
    petId: response.id,
    name: response.name,
    species: speciesFromApi[response.species],
    speciesDetail: response.speciesDetail ?? undefined,
    breed: response.breed,
    birthDate: response.birthDate,
    age: response.age,
    weight: response.weightKg,
    size: response.size ? sizeFromApi[response.size] : null,
    profileImage: response.imageUrl ?? undefined,
    isPrimary: response.isPrimary,
    status: response.status,
  };
}

function toPayload(input: PetFormInput) {
  return {
    name: input.name.trim(),
    species: speciesToApi[input.species],
    speciesDetail: input.species === '기타' ? input.speciesDetail?.trim() : undefined,
    breed: input.breed.trim(),
    birthDate: input.birthDate,
    weightKg: input.weight,
    size: sizeToApi[input.size],
    ...(input.localProfileImageUri ? { imageUrl: input.localProfileImageUri } : {}),
    ...(input.removeProfileImage ? { imageUrl: null } : {}),
  };
}

export async function fetchPets(): Promise<Pet[]> {
  const response = await apiClient.get<PetListApiResponse>('/pets');
  return response.data.items.map(toPet);
}

export async function fetchAllPets(): Promise<Pet[]> {
  const response = await apiClient.get<PetListApiResponse>('/pets', {
    params: { includeDeleted: true },
  });
  return response.data.items.map(toPet);
}

export async function uploadPetImage(localUri: string): Promise<string> {
  return uploadImage(localUri, 'pet');
}

export async function createPet(input: PetFormInput): Promise<Pet> {
  const response = await apiClient.post<PetApiResponse>('/pets', toPayload(input));
  return toPet(response.data);
}

export async function updatePet(petId: string, input: PetFormInput): Promise<Pet> {
  const response = await apiClient.patch<PetApiResponse>(`/pets/${petId}`, toPayload(input));
  return toPet(response.data);
}

export async function deletePet(petId: string): Promise<string> {
  await apiClient.delete(`/pets/${petId}`);
  return petId;
}

export function toPetSnapshot(pet: Pet): TravelLogPetSnapshot {
  return {
    petId: pet.petId,
    nameSnapshot: pet.name,
    profileImageSnapshot: pet.profileImage,
  };
}

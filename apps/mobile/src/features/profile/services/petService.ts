import type { Pet, PetSpecies } from '@/src/types/pet';
import type { TravelLogPetSnapshot } from '@/src/types/travelLog';
import { createId } from '@/src/utils/createId';

import { mockPets } from '../mocks/profile.mock';

const FETCH_DELAY_MS = 300;
const UPLOAD_DELAY_MS = 400;
const MUTATION_DELAY_MS = 300;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 세션 내 메모리 저장소. soft delete된 프로필도 계속 남는다.
 * TODO: 실제 API 연동 시 이 배열 접근을 apiClient 호출로 교체 (pets 테이블)
 */
let currentPets: Pet[] = mockPets.map((pet) => ({ ...pet }));

export type PetFormInput = {
  name: string;
  species: PetSpecies;
  breed: string;
  age: number;
  weight: number;
  /** 새로 고른 로컬 이미지. removeProfileImage와 동시에 지정할 수 없다. */
  localProfileImageUri?: string;
  /** 기본 이미지로 되돌리기. localProfileImageUri와 동시에 지정할 수 없다. */
  removeProfileImage?: boolean;
};

export class PetNotFoundError extends Error {
  constructor(petId: string) {
    super(`반려동물을 찾을 수 없습니다: ${petId}`);
    this.name = 'PetNotFoundError';
  }
}

export class PetAlreadyDeletedError extends Error {
  constructor(petId: string) {
    super(`이미 지워진 반려동물입니다: ${petId}`);
    this.name = 'PetAlreadyDeletedError';
  }
}

/** 화면에 노출되는 목록. 지워진 프로필은 절대 포함하지 않는다. */
export async function fetchPets(): Promise<Pet[]> {
  await wait(FETCH_DELAY_MS);
  return currentPets.filter((pet) => pet.status === 'active').map((pet) => ({ ...pet }));
}

/**
 * 지워진 프로필까지 포함한 전체 목록.
 * 과거 기록의 필터 옵션처럼 "지금은 없지만 기록에는 남아있는" 반려동물을 다뤄야 할 때만 쓴다.
 */
export async function fetchAllPets(): Promise<Pet[]> {
  await wait(FETCH_DELAY_MS);
  return currentPets.map((pet) => ({ ...pet }));
}

export async function uploadPetImage(localUri: string): Promise<string> {
  await wait(UPLOAD_DELAY_MS);
  return localUri;
}

/**
 * 입력의 이미지 의도(유지/교체/기본값)를 실제 저장할 URL로 변환한다.
 * 두 플래그가 동시에 켜지면 사용자의 마지막 의도를 알 수 없으므로 명시적으로 막는다.
 */
function resolveProfileImage(input: PetFormInput, previous: string | undefined): string | undefined {
  if (input.localProfileImageUri && input.removeProfileImage) {
    throw new Error('이미지 교체와 기본 이미지 변경을 동시에 요청할 수 없습니다.');
  }
  if (input.removeProfileImage) return undefined;
  return input.localProfileImageUri ?? previous;
}

function toPetFields(input: PetFormInput) {
  return {
    name: input.name.trim(),
    species: input.species,
    breed: input.breed.trim(),
    age: input.age,
    weight: input.weight,
  };
}

/**
 * 항상 새 petId를 발급한다. 같은 이름의 지워진 프로필이 있어도
 * 복원하거나 재사용하지 않는다 — 이름이 같을 뿐 다른 개체이기 때문이다.
 */
export async function createPet(input: PetFormInput): Promise<Pet> {
  await wait(MUTATION_DELAY_MS);

  const created: Pet = {
    petId: createId('pet'),
    ...toPetFields(input),
    profileImage: resolveProfileImage(input, undefined),
    status: 'active',
  };

  currentPets = [...currentPets, created];
  return { ...created };
}

export async function updatePet(petId: string, input: PetFormInput): Promise<Pet> {
  await wait(MUTATION_DELAY_MS);

  const index = currentPets.findIndex((pet) => pet.petId === petId);
  if (index === -1) throw new PetNotFoundError(petId);

  const previous = currentPets[index];
  if (previous.status === 'deleted') throw new PetAlreadyDeletedError(petId);

  const updated: Pet = {
    ...previous,
    ...toPetFields(input),
    profileImage: resolveProfileImage(input, previous.profileImage),
  };

  currentPets = currentPets.map((pet) => (pet.petId === petId ? updated : pet));
  return { ...updated };
}

/**
 * soft delete. 배열에서 제거하지 않으므로 과거 기록이 참조하는 petId는 그대로 살아있다.
 * 이미 지워진 프로필에 다시 요청이 오면 deletedAt을 덮어쓰지 않고 에러로 막는다.
 */
export async function deletePet(petId: string): Promise<Pet> {
  await wait(MUTATION_DELAY_MS);

  const target = currentPets.find((pet) => pet.petId === petId);
  if (!target) throw new PetNotFoundError(petId);
  if (target.status === 'deleted') throw new PetAlreadyDeletedError(petId);

  const deleted: Pet = { ...target, status: 'deleted', deletedAt: new Date().toISOString() };
  currentPets = currentPets.map((pet) => (pet.petId === petId ? deleted : pet));
  return { ...deleted };
}

/**
 * 기록 저장 시점에 박제할 스냅샷을 만든다.
 * 이후 이 반려동물의 이름·사진이 바뀌거나 프로필이 지워져도 이 값은 변하지 않는다.
 */
export function toPetSnapshot(pet: Pet): TravelLogPetSnapshot {
  return {
    petId: pet.petId,
    nameSnapshot: pet.name,
    profileImageSnapshot: pet.profileImage,
  };
}

/** 목업 저장소를 초기 상태로 되돌린다. 검증 스크립트 전용. */
export function __resetPetsForTest(): void {
  currentPets = mockPets.map((pet) => ({ ...pet }));
}

export type PetSpecies = '강아지' | '고양이';

/** 선택 UI(칩)와 타입이 어긋나지 않도록 목록은 union에서 파생시킨다. */
export const PET_SPECIES_OPTIONS: PetSpecies[] = ['강아지', '고양이'];

/**
 * 프로필은 물리 삭제하지 않는다. 과거 여행 기록이 참조하는 petId가 사라지면
 * 기록 자체가 깨지므로, 지우기는 status를 'deleted'로 바꾸는 soft delete로 처리한다.
 */
export type PetStatus = 'active' | 'deleted';

export interface Pet {
  petId: string;
  name: string;
  species: PetSpecies;
  breed: string;
  age: number;
  weight: number;
  profileImage?: string;
  status: PetStatus;
  /** status가 'deleted'일 때만 채워진다. ISO datetime */
  deletedAt?: string;
}

export function isActivePet(pet: Pet): boolean {
  return pet.status === 'active';
}

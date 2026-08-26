export type PetSpecies = '강아지' | '고양이' | '기타';

/** 선택 UI(칩)와 타입이 어긋나지 않도록 목록은 union에서 파생시킨다. */
export const PET_SPECIES_OPTIONS: PetSpecies[] = ['강아지', '고양이', '기타'];

/** '기타'를 고르면 종 이름을 직접 받는다. */
export const OTHER_SPECIES: PetSpecies = '기타';

/**
 * 크기는 몸무게와 별개로 둔다.
 * 장소의 동반 정책이 '소형견만'(allowed_sizes)과 '10kg 이하'(max_weight_kg) 두 가지로
 * 나뉘어 있어, 둘 중 하나만으로는 동반 가능 여부를 판단할 수 없다.
 */
export type PetSize = '소형' | '중형' | '대형';

export const PET_SIZE_OPTIONS: PetSize[] = ['소형', '중형', '대형'];

const MEDIUM_MIN_KG = 10;
const LARGE_MIN_KG = 25;

/**
 * 몸무게로 크기를 추정한다. 입력을 줄여주는 기본값일 뿐 강제하지 않는다.
 * 닥스훈트처럼 무게와 체감 크기가 다른 경우가 있어 사용자가 고른 값이 언제나 우선한다.
 */
export function suggestPetSize(weightKg: number): PetSize | null {
  if (!Number.isFinite(weightKg) || weightKg <= 0) return null;
  if (weightKg < MEDIUM_MIN_KG) return '소형';
  if (weightKg <= LARGE_MIN_KG) return '중형';
  return '대형';
}

/**
 * 프로필은 물리 삭제하지 않는다. 과거 여행 기록이 참조하는 petId가 사라지면
 * 기록 자체가 깨지므로, 지우기는 status를 'deleted'로 바꾸는 soft delete로 처리한다.
 */
export type PetStatus = 'active' | 'deleted';

export interface Pet {
  petId: string;
  name: string;
  species: PetSpecies;
  /** species가 '기타'일 때만 채워진다. 사용자가 직접 적은 종 이름 */
  speciesDetail?: string;
  breed: string | null;
  birthDate: string | null;
  age: number | null;
  weight: number | null;
  size: PetSize | null;
  profileImage?: string;
  isPrimary: boolean;
  status: PetStatus;
}

export function isActivePet(pet: Pet): boolean {
  return pet.status === 'active';
}

/** 화면에 보여줄 종 이름. '기타'면 사용자가 적은 이름을 쓴다. */
export function formatSpecies(pet: Pick<Pet, 'species' | 'speciesDetail'>): string {
  if (pet.species !== OTHER_SPECIES) return pet.species;
  return pet.speciesDetail?.trim() || OTHER_SPECIES;
}

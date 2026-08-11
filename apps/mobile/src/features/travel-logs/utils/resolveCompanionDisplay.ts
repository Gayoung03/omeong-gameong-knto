import type { Pet } from '@/src/types/pet';
import type { TravelLogPetSnapshot } from '@/src/types/travelLog';

export type CompanionDisplay = {
  petId: string;
  name: string;
  profileImage?: string;
};

/**
 * 기록에 달린 반려동물 태그를 화면에 그릴 때 쓸 이름·사진을 정한다.
 *
 * petId는 절대 바뀌지 않는 불변 식별자이므로, 이름과 사진은 현재 Pet 레코드에서 가져와
 * 최신 정보를 반영한다. 프로필을 지워도 soft delete라 레코드가 남아있어 태그는 그대로 보인다.
 *
 * 스냅샷은 Pet 레코드 자체를 찾지 못할 때(향후 물리 삭제로 pet_id가 NULL이 되는 경우 등)의
 * fallback으로만 쓴다. 연결 관계는 언제나 petId로 고정되므로 같은 이름으로 재등록한
 * 다른 개체와 섞이지 않는다.
 */
export function resolveCompanionDisplay(
  companion: TravelLogPetSnapshot,
  petsById: Map<string, Pet>,
): CompanionDisplay {
  const pet = petsById.get(companion.petId);

  // 레코드를 찾았으면 이름·사진 모두 현재 값을 쓴다. 사진을 기본 이미지로 되돌린 경우
  // profileImage가 비는데, 이때 스냅샷으로 되돌아가면 지운 사진이 과거 기록에 남는다.
  if (pet) {
    return { petId: companion.petId, name: pet.name, profileImage: pet.profileImage };
  }

  return {
    petId: companion.petId,
    name: companion.nameSnapshot,
    profileImage: companion.profileImageSnapshot,
  };
}

export function toPetsById(pets: Pet[]): Map<string, Pet> {
  return new Map(pets.map((pet) => [pet.petId, pet]));
}

export function resolveCompanions(
  companions: TravelLogPetSnapshot[],
  petsById: Map<string, Pet>,
): CompanionDisplay[] {
  return companions.map((companion) => resolveCompanionDisplay(companion, petsById));
}

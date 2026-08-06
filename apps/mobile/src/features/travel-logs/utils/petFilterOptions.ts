import type { Pet } from '@/src/types/pet';
import type { TravelLogPetSnapshot } from '@/src/types/travelLog';

/** 로그 필터에 노출할 반려동물 항목. 활성 프로필과 지워진 프로필을 함께 담는다. */
export type PetLogFilterOption = {
  petId: string;
  label: string;
  profileImage?: string;
  isArchived: boolean;
};

const ARCHIVED_SUFFIX = ' · 이전 프로필';

/**
 * 필터 옵션을 만든다. 이름·이미지의 1순위 출처는 언제나 현재 Pet 데이터(fetchAllPets)다.
 * 한 반려동물이 이름을 여러 번 바꿨다면 로그마다 다른 nameSnapshot이 남아 있으므로,
 * 스냅샷은 Pet 레코드 자체를 찾지 못할 때의 fallback으로만 쓴다.
 *
 * 같은 이름이어도 petId가 다르면 절대 합치지 않는다.
 */
export function buildPetFilterOptions(
  allPets: Pet[],
  companionsInLogs: TravelLogPetSnapshot[],
): PetLogFilterOption[] {
  const options = new Map<string, PetLogFilterOption>();

  for (const pet of allPets) {
    const isArchived = pet.status === 'deleted';
    options.set(pet.petId, {
      petId: pet.petId,
      label: isArchived ? `${pet.name}${ARCHIVED_SUFFIX}` : pet.name,
      profileImage: pet.profileImage,
      isArchived,
    });
  }

  // Pet 레코드가 아예 없는 경우(향후 물리 삭제 등)에만 기록의 스냅샷으로 이름을 채운다.
  for (const companion of companionsInLogs) {
    if (options.has(companion.petId)) continue;

    options.set(companion.petId, {
      petId: companion.petId,
      label: `${companion.nameSnapshot}${ARCHIVED_SUFFIX}`,
      profileImage: companion.profileImageSnapshot,
      isArchived: true,
    });
  }

  // 활성 프로필을 먼저, 지워진 프로필을 뒤에 둔다.
  return [...options.values()].sort((a, b) => Number(a.isArchived) - Number(b.isArchived));
}

/** 목록 아이템들이 참조하는 모든 반려동물 스냅샷을 petId 기준으로 모은다. */
export function collectCompanions(
  sources: { companions: TravelLogPetSnapshot[] }[],
): TravelLogPetSnapshot[] {
  const byPetId = new Map<string, TravelLogPetSnapshot>();

  for (const source of sources) {
    for (const companion of source.companions) {
      if (!byPetId.has(companion.petId)) {
        byPetId.set(companion.petId, companion);
      }
    }
  }

  return [...byPetId.values()];
}

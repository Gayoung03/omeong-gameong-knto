import { fetchPets, toPetSnapshot } from '@/src/features/profile/services/petService';
import type { GenerationStatus, LogDraft } from '@/src/types/logDraft';
import type { TravelLog, TravelLogPetSnapshot } from '@/src/types/travelLog';

import { mockLogs } from '../mocks/travelLogMocks';

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, milliseconds);
  });

function validateDraft(draft: LogDraft) {
  if (
    !draft.localPhotoUri ||
    !draft.recordedDate ||
    !draft.placeName ||
    draft.petIds.length === 0 ||
    !draft.writingStyle ||
    !draft.mood
  ) {
    throw new Error('INVALID_DRAFT');
  }
}

/**
 * 저장 시점의 활성 반려동물 정보를 스냅샷으로 박제한다.
 * 이미 지워진 프로필이 draft에 남아 있더라도 새 기록에는 포함하지 않는다.
 */
async function buildCompanions(petIds: string[]): Promise<TravelLogPetSnapshot[]> {
  const activePets = await fetchPets();

  return activePets.filter((pet) => petIds.includes(pet.petId)).map(toPetSnapshot);
}

export const mockLogService = {
  async generateLog(
    draft: LogDraft,
    onStatus: (status: Extract<GenerationStatus, 'uploading' | 'generating'>) => void,
  ): Promise<TravelLog> {
    validateDraft(draft);
    onStatus('uploading');
    await wait(650);
    onStatus('generating');
    await wait(2200);

    const preparedGeneratedImage = mockLogs[0]?.generatedImageUrl;
    if (!preparedGeneratedImage) throw new Error('GENERATION_FAILED');

    const companions = await buildCompanions(draft.petIds);
    const createdAt = new Date().toISOString();
    return {
      logId: `generated-${Date.now()}`,
      tripId: draft.tripId ?? null,
      recordedDate: draft.recordedDate!,
      visitedAt: `${draft.recordedDate}T12:00:00`,
      createdAt,
      placeId: draft.placeId ?? null,
      placeName: draft.placeName!,
      originalImageUrl: `mock-upload://${encodeURIComponent(draft.photoFileName ?? 'photo')}`,
      generatedImageUrl: preparedGeneratedImage,
      personalMessage: draft.personalMessage.trim() || null,
      companions,
      isRepresentative: true,
    };
  },

  async saveLog(log: TravelLog): Promise<TravelLog> {
    await wait(450);
    return log;
  },
};

import { create } from 'zustand';

import { uploadImage } from '@/src/services/uploadImage';
import {
  initialLogDraft,
  type GenerationResult,
  type GenerationStatus,
  type LogDraft,
} from '@/src/types/logDraft';

import {
  createTravelLog,
  regenerateTravelLog,
  waitForGeneration,
} from '../api/travelLogsApi';

type LogDraftState = {
  draft: LogDraft;
  generationStatus: GenerationStatus;
  generatedLog: GenerationResult | null;
  errorMessage: string | null;
  updateDraft: (values: Partial<LogDraft>) => void;
  resetDraft: () => void;
  startGeneration: () => Promise<void>;
  regenerate: () => Promise<void>;
};

const FAILURE_MESSAGE = '여행 기록을 만들지 못했어요. 잠시 후 다시 시도해 주세요.';

function isIncomplete(draft: LogDraft): boolean {
  return (
    !draft.localPhotoUri ||
    !draft.recordedDate ||
    !draft.placeName ||
    draft.petIds.length === 0 ||
    !draft.writingStyle ||
    !draft.mood
  );
}

export const useLogDraftStore = create<LogDraftState>((set, get) => ({
  draft: initialLogDraft,
  generationStatus: 'idle',
  generatedLog: null,
  errorMessage: null,
  updateDraft: (values) => set((state) => ({ draft: { ...state.draft, ...values } })),
  resetDraft: () =>
    set({
      draft: initialLogDraft,
      generationStatus: 'idle',
      generatedLog: null,
      errorMessage: null,
    }),

  /**
   * 사진을 올리고 기록을 만든다.
   *
   * 서버는 "접수했다"고만 먼저 답하므로 완료될 때까지 상태를 확인한다.
   * 화면은 `generationStatus` 만 보고 그리고, 그 값의 이름은 서버와 같다.
   */
  startGeneration: async () => {
    const { generationStatus, draft } = get();
    if (generationStatus === 'uploading' || generationStatus === 'generating') return;

    set({ generationStatus: 'uploading', generatedLog: null, errorMessage: null });

    if (isIncomplete(draft)) {
      set({ errorMessage: FAILURE_MESSAGE, generationStatus: 'failed' });
      return;
    }

    try {
      // 사진이 서버에 올라가야 기록을 만들 수 있다. 앱은 로컬 경로를 보내지 않는다.
      const originalImageUrl = await uploadImage(draft.localPhotoUri!, 'travel_log');

      const { id } = await createTravelLog({
        routeId: draft.tripId ?? null,
        placeId: draft.placeId,
        placeName: draft.placeName!,
        recordedDate: draft.recordedDate!,
        originalImageUrl,
        writingStyle: draft.writingStyle,
        mood: draft.mood,
        personalMessage: draft.personalMessage.trim() || null,
        petIds: draft.petIds,
      });

      const generatedLog = await waitForGeneration(id, (status) =>
        set({ generationStatus: status }),
      );
      set({ generatedLog, generationStatus: 'completed' });
    } catch {
      set({ errorMessage: FAILURE_MESSAGE, generationStatus: 'failed' });
    }
  },

  /**
   * 이미 만들어진 기록의 이미지만 다시 만든다.
   *
   * `startGeneration` 을 다시 부르면 **기록이 하나 더 생긴다.** 완료 화면의
   * "다시 만들기"는 같은 기록을 고치려는 것이므로 이쪽을 쓴다.
   */
  regenerate: async () => {
    const { generatedLog, generationStatus } = get();
    if (!generatedLog) return;
    if (generationStatus === 'uploading' || generationStatus === 'generating') return;

    set({ generationStatus: 'generating', errorMessage: null });
    try {
      await regenerateTravelLog(generatedLog.logId);
      const updated = await waitForGeneration(generatedLog.logId, (status) =>
        set({ generationStatus: status }),
      );
      set({ generatedLog: updated, generationStatus: 'completed' });
    } catch {
      set({ errorMessage: FAILURE_MESSAGE, generationStatus: 'failed' });
    }
  },
}));

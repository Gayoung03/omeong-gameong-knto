import { create } from 'zustand';

import { uploadImage } from '@/src/services/uploadImage';
import {
  initialLogDraft,
  type GenerationResult,
  type GenerationStatus,
  type LogDraft,
} from '@/src/types/logDraft';

import {
  GenerationFailedError,
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
const INCOMPLETE_MESSAGE = '빠진 항목이 있어요. 이전 단계에서 다시 확인해 주세요.';

/**
 * 화면에 띄울 실패 문구를 고른다.
 *
 * 서버가 사유를 준 경우에는 **그것을 그대로 쓴다.** 사유마다 사용자가 할 행동이
 * 다르기 때문이다 — 사진이 걸린 것이면 다시 눌러도 또 걸리므로 "잠시 후 다시"는
 * 틀린 안내이고, 재시도 한 번마다 카드 한 장 값이 나간다.
 */
function describeFailure(error: unknown): string {
  if (error instanceof GenerationFailedError && error.userMessage) return error.userMessage;
  return FAILURE_MESSAGE;
}

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
      // 서버에 가보지도 않은 경우다. "잠시 후 다시"는 아무것도 고쳐주지 않는다.
      set({ errorMessage: INCOMPLETE_MESSAGE, generationStatus: 'failed' });
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
    } catch (error) {
      set({ errorMessage: describeFailure(error), generationStatus: 'failed' });
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
    } catch (error) {
      set({ errorMessage: describeFailure(error), generationStatus: 'failed' });
    }
  },
}));

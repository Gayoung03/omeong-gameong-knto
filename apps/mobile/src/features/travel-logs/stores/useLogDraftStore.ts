import { create } from 'zustand';

import {
  initialLogDraft,
  type GenerationResult,
  type GenerationStatus,
  type LogDraft,
} from '@/src/types/logDraft';

import { mockLogService } from '../services/mockLogService';

type LogDraftState = {
  draft: LogDraft;
  generationStatus: GenerationStatus;
  generatedLog: GenerationResult | null;
  errorMessage: string | null;
  updateDraft: (values: Partial<LogDraft>) => void;
  resetDraft: () => void;
  startGeneration: () => Promise<void>;
};

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
  startGeneration: async () => {
    const { generationStatus, draft } = get();
    if (generationStatus === 'uploading' || generationStatus === 'generating') return;

    set({ generationStatus: 'uploading', generatedLog: null, errorMessage: null });
    try {
      const generatedLog = await mockLogService.generateLog(draft, (status) =>
        set({ generationStatus: status }),
      );
      set({ generatedLog, generationStatus: 'completed' });
    } catch {
      set({
        errorMessage: '여행 기록을 만들지 못했어요. 잠시 후 다시 시도해 주세요.',
        generationStatus: 'failed',
      });
    }
  },
}));

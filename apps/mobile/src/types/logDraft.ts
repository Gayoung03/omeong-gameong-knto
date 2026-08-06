import type { TravelLog } from './travelLog';

export type WritingStyle = 'dog_diary' | 'jeju_dialect';
export type MomentMood = 'happy' | 'excited' | 'relaxed' | 'bittersweet';
export type GenerationStatus = 'idle' | 'uploading' | 'generating' | 'completed' | 'failed';

export type LogDraft = {
  localPhotoUri: string | null;
  photoFileName?: string;
  photoMimeType?: string;
  photoFileSize?: number;
  photoWidth?: number;
  photoHeight?: number;
  tripId?: string;
  recordedDate: string | null;
  placeId?: string;
  placeName: string | null;
  petIds: string[];
  writingStyle: WritingStyle;
  mood: MomentMood | null;
  personalMessage: string;
};

export type GenerationResult = TravelLog;

export const initialLogDraft: LogDraft = {
  localPhotoUri: null,
  recordedDate: null,
  placeName: null,
  petIds: [],
  writingStyle: 'dog_diary',
  mood: null,
  personalMessage: '',
};

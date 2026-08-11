import type { Place } from '@/src/features/places/types/place';

export type ChatMessage = {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  mapPlaces?: Place[];
};

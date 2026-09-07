import { apiClient } from '@/src/services/apiClient';

import type { EditorialStory } from '../types/home';

type EditorialStoryListResponse = {
  items: EditorialStory[];
  total: number;
};

export async function fetchEditorialStories(): Promise<EditorialStory[]> {
  const { data } = await apiClient.get<EditorialStoryListResponse>('/editorial-stories', {
    params: { limit: 4 },
  });
  return data.items;
}

export async function fetchEditorialStory(storyId: string): Promise<EditorialStory> {
  const { data } = await apiClient.get<EditorialStory>(`/editorial-stories/${storyId}`);
  return data;
}

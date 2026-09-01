import { apiClient } from '@/src/services/apiClient';
import type { NoticeItem } from '@/src/types/notice';

type NoticeResponse = {
  id: string;
  title: string;
  content?: string;
  publishedAt: string;
};

function toNotice(item: NoticeResponse): NoticeItem {
  return {
    id: item.id,
    title: item.title,
    content: item.content ?? '',
    createdAt: new Date(item.publishedAt).toLocaleDateString('ko-KR').replaceAll(' ', ''),
  };
}

export async function fetchNotices(): Promise<NoticeItem[]> {
  const { data } = await apiClient.get<{ items: NoticeResponse[] }>('/notices');
  return data.items.map(toNotice);
}

export async function fetchNotice(id: string): Promise<NoticeItem> {
  const { data } = await apiClient.get<NoticeResponse>(`/notices/${id}`);
  return toNotice(data);
}

import { apiClient } from '@/src/services/apiClient';

import { toChecklistCategory } from '../constants/checklist';
import type { ChecklistCategory, ChecklistItem } from '../types/trip';

/**
 * 여행 준비 체크리스트 서버 호출.
 *
 * 일정 항목(`route_items`)과 달리 `sortOrder` 에 UNIQUE 가 없어서
 * 순번을 다시 매기는 절차가 없다. 앱이 보낸 값을 서버가 그대로 쓴다.
 */

type ChecklistItemResponse = {
  id: string;
  category: string;
  label: string;
  isChecked: boolean;
  isRecommended: boolean;
  sortOrder: number;
};

type ChecklistListResponse = {
  items: ChecklistItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

function toChecklistItem(response: ChecklistItemResponse): ChecklistItem {
  return {
    category: toChecklistCategory(response.category),
    id: response.id,
    isChecked: response.isChecked,
    isRecommended: response.isRecommended,
    label: response.label,
  };
}

export async function getChecklistItems(tripId: string): Promise<ChecklistItem[]> {
  const { data } = await apiClient.get<ChecklistListResponse>(
    `/routes/${tripId}/checklist-items`,
    { params: { limit: 200 } },
  );
  return data.items.map(toChecklistItem);
}

export async function addChecklistItem(
  tripId: string,
  payload: { label: string; category: ChecklistCategory; sortOrder: number },
): Promise<ChecklistItem> {
  // isRecommended 는 보내지 않는다. 서버가 false 로 고정한다 —
  // 사용자가 만든 항목이 '기본 제공'으로 둔갑하지 않게 하려는 것이다.
  const { data } = await apiClient.post<ChecklistItemResponse>(
    `/routes/${tripId}/checklist-items`,
    payload,
  );
  return toChecklistItem(data);
}

export async function updateChecklistItem(
  itemId: string,
  payload: { isChecked?: boolean; label?: string; sortOrder?: number },
): Promise<ChecklistItem> {
  const { data } = await apiClient.patch<ChecklistItemResponse>(
    `/checklist-items/${itemId}`,
    payload,
  );
  return toChecklistItem(data);
}

export async function removeChecklistItem(itemId: string): Promise<void> {
  await apiClient.delete(`/checklist-items/${itemId}`);
}

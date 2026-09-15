import { useEffect, useState } from 'react';

import { apiRequest } from './api';
import type { StoryListResponse } from '../types';

/** 승인·보관·초안 복귀로 검수 대기 수가 바뀌었을 때 쏘면 배지가 갱신된다. */
export const STORIES_CHANGED_EVENT = 'omeong-admin-stories-changed';

const POLL_MS = 60_000;

/**
 * 검수 대기(draft) 여행 이야기 수. 사이드바 배지에 쓴다.
 * 기존 관리자 목록 API 의 total 을 그대로 쓴다. 로딩·오류 중에는 null.
 */
export function usePendingStoryCount(): number | null {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      apiRequest<StoryListResponse>('/admin/editorial-stories?status=draft&limit=1')
        .then((data) => {
          if (!cancelled) setCount(data.total);
        })
        .catch(() => {
          if (!cancelled) setCount(null);
        });
    };

    load();
    const timer = window.setInterval(load, POLL_MS);
    window.addEventListener('focus', load);
    window.addEventListener(STORIES_CHANGED_EVENT, load);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener('focus', load);
      window.removeEventListener(STORIES_CHANGED_EVENT, load);
    };
  }, []);

  return count;
}

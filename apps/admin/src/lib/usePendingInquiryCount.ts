import { useEffect, useState } from 'react';

import { apiRequest } from './api';
import type { AdminInquiryListResponse } from '../types';

/** 답변 등록 등으로 미답변 수가 바뀌었을 때 이 이벤트를 쏘면 배지가 갱신된다. */
export const INQUIRIES_CHANGED_EVENT = 'omeong-admin-inquiries-changed';

const POLL_MS = 60_000;

/**
 * 미답변(`status=pending`) 1:1 문의 건수. 사이드바 배지에 쓴다.
 * 60초 폴링 + 창 포커스 + `INQUIRIES_CHANGED_EVENT` 로 갱신한다.
 * 로딩·오류 중에는 `null` 을 돌려 배지를 숨긴다(틀린 숫자를 안 보여준다).
 */
export function usePendingInquiryCount(): number | null {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      apiRequest<AdminInquiryListResponse>('/admin/inquiries?status=pending&limit=1')
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
    window.addEventListener(INQUIRIES_CHANGED_EVENT, load);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener('focus', load);
      window.removeEventListener(INQUIRIES_CHANGED_EVENT, load);
    };
  }, []);

  return count;
}

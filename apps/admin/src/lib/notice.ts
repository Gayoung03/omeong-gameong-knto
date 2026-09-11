export const NOTICE_STATUS_LABEL: Record<string, string> = {
  draft: '초안',
  live: '게시 중',
  stopped: '게시 중단',
};

/** 발송 여부(announcedAt)와 노출 여부(isActive)로 화면용 상태를 만든다. */
export function noticeDisplayStatus(item: {
  announcedAt: string | null;
  isActive: boolean;
}): 'draft' | 'live' | 'stopped' {
  if (!item.announcedAt) return 'draft';
  return item.isActive ? 'live' : 'stopped';
}

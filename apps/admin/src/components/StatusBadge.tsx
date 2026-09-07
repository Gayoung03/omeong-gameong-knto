import type { StoryStatus } from '../types';

const STATUS_LABEL: Record<StoryStatus, string> = {
  draft: '초안',
  published: '게시 중',
  archived: '보관',
};

export function StatusBadge({ status }: { status: StoryStatus }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABEL[status]}</span>;
}

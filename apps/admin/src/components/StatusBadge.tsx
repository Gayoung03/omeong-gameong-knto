const STORY_STATUS_LABEL: Record<string, string> = {
  draft: '초안',
  published: '게시 중',
  archived: '보관',
};

interface StatusBadgeProps {
  status: string;
  /** 코드→라벨 맵. 생략하면 여행 이야기 상태 라벨을 쓴다. */
  labels?: Record<string, string>;
}

export function StatusBadge({ status, labels = STORY_STATUS_LABEL }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${status}`}>{labels[status] ?? status}</span>
  );
}

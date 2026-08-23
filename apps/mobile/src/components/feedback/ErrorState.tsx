import { EmptyState } from './EmptyState';

type ErrorStateProps = {
  title?: string;
  description?: string;
  retryLabel?: string;
  onRetry: () => void;
};

/**
 * 데이터 조회에 실패했을 때 쓰는 공용 에러 화면.
 * 화면마다 따로 만들지 않고 이걸 쓴다. EmptyState 와 시각적으로 같은 언어를 쓴다.
 */
export function ErrorState({
  title = '정보를 불러오지 못했어요',
  description = '잠시 후 다시 시도해 주세요.',
  retryLabel = '다시 시도',
  onRetry,
}: ErrorStateProps) {
  return (
    <EmptyState
      actionLabel={retryLabel}
      description={description}
      icon="cloud-offline-outline"
      onPressAction={onRetry}
      title={title}
    />
  );
}

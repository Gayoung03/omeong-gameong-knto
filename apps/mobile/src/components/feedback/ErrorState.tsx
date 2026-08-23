import { getApiErrorMessage } from '@/src/services/apiError';

import { EmptyState } from './EmptyState';

type ErrorStateProps = {
  description?: string;
  error?: unknown;
  onRetry: () => void;
  retryLabel?: string;
  title?: string;
};

/**
 * 데이터 조회에 실패했을 때 쓰는 공용 에러 화면.
 * 화면마다 따로 만들지 않고 이걸 쓴다. EmptyState 와 시각적으로 같은 언어를 쓴다.
 */
export function ErrorState({
  description,
  error,
  onRetry,
  retryLabel,
  title,
}: ErrorStateProps) {
  const apiError = error === undefined ? undefined : getApiErrorMessage(error);
  const retryAction = apiError?.retryable === false ? undefined : onRetry;

  return (
    <EmptyState
      actionLabel={
        retryAction ? (retryLabel ?? apiError?.actionLabel ?? '다시 시도') : undefined
      }
      description={description ?? apiError?.description ?? '잠시 후 다시 시도해 주세요.'}
      icon={apiError?.icon ?? 'cloud-offline-outline'}
      onPressAction={retryAction}
      title={title ?? apiError?.title ?? '정보를 불러오지 못했어요'}
    />
  );
}

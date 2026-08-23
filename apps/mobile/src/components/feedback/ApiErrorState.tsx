import { useMemo } from 'react';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { getApiErrorMessage } from '@/src/services/apiError';

type ApiErrorStateProps = {
  error: unknown;
  onRetry?: () => void;
  title?: string;
};

/** API/네트워크 실패 원인과 다음 행동을 기술 용어 없이 안내한다. */
export function ApiErrorState({ error, onRetry, title }: ApiErrorStateProps) {
  const message = useMemo(() => getApiErrorMessage(error), [error]);
  const retryAction = message.retryable ? onRetry : undefined;

  return (
    <EmptyState
      actionLabel={retryAction ? message.actionLabel : undefined}
      description={message.description}
      icon={message.icon}
      onPressAction={retryAction}
      title={title ?? message.title}
    />
  );
}

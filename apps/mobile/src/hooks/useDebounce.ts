import { useEffect, useState } from 'react';

/**
 * 값이 delayMs 동안 더 이상 바뀌지 않을 때만 갱신되는 파생 값을 반환한다.
 * 입력창 자체는 즉시 갱신하고, 필터링 등 비용이 큰 파생 계산에만 이 값을 사용한다.
 */
export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delayMs);

    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}

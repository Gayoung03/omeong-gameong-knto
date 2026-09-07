import { isAxiosError } from 'axios';

import { getApiErrorMessage } from '@/src/services/apiError';

/**
 * 대화 목록·휴지통에서 실패했을 때 사용자에게 보여줄 한 줄.
 *
 * **409 만 서버 문구를 그대로 쓴다.** 복구를 거절할 때 서버가 보내는
 * "대화는 100개까지 가질 수 있어요. 안 쓰는 대화를 지워주세요"는 이미 사용자를
 * 향해 쓴 문장이고, 무엇을 하면 되는지까지 알려준다. 공통 문구
 * ("이미 처리된 요청인지 확인해 주세요")로 덮으면 사용자는 왜 안 되는지 모른다.
 *
 * 나머지 상태 코드는 공통 규약(`services/apiError.ts`)을 따른다.
 */
export function conversationErrorText(error: unknown): string {
  if (isAxiosError(error) && error.response?.status === 409) {
    const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  return getApiErrorMessage(error).description;
}

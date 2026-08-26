import { isAxiosError } from 'axios';

export type ApiErrorKind =
  | 'network'
  | 'timeout'
  | 'authentication'
  | 'badRequest'
  | 'permission'
  | 'notFound'
  | 'conflict'
  | 'fileTooLarge'
  | 'unsupportedFile'
  | 'validation'
  | 'rateLimit'
  | 'server'
  | 'unknown';

export type ApiErrorMessage = {
  actionLabel: string;
  description: string;
  icon: 'alert-circle-outline' | 'cloud-offline-outline' | 'lock-closed-outline' | 'time-outline';
  kind: ApiErrorKind;
  retryable: boolean;
  title: string;
};

const ERROR_MESSAGES: Record<ApiErrorKind, ApiErrorMessage> = {
  network: {
    actionLabel: '다시 시도',
    description: '인터넷 연결을 확인한 뒤 다시 시도해 주세요.',
    icon: 'cloud-offline-outline',
    kind: 'network',
    retryable: true,
    title: '네트워크에 연결할 수 없어요',
  },
  timeout: {
    actionLabel: '다시 시도',
    description: '연결이 원활하지 않아요. 잠시 후 다시 시도해 주세요.',
    icon: 'time-outline',
    kind: 'timeout',
    retryable: true,
    title: '응답이 너무 오래 걸리고 있어요',
  },
  authentication: {
    actionLabel: '로그인하기',
    description: '안전한 이용을 위해 다시 로그인해 주세요.',
    icon: 'lock-closed-outline',
    kind: 'authentication',
    retryable: false,
    title: '로그인이 만료되었어요',
  },
  badRequest: {
    actionLabel: '확인',
    description: '현재 상태에서는 요청을 처리할 수 없어요. 입력 내용을 확인해 주세요.',
    icon: 'alert-circle-outline',
    kind: 'badRequest',
    retryable: false,
    title: '요청을 처리할 수 없어요',
  },
  permission: {
    actionLabel: '확인',
    description: '이 내용에 접근할 권한이 있는지 확인해 주세요.',
    icon: 'lock-closed-outline',
    kind: 'permission',
    retryable: false,
    title: '접근할 수 없어요',
  },
  notFound: {
    actionLabel: '돌아가기',
    description: '삭제되었거나 더 이상 이용할 수 없는 내용이에요.',
    icon: 'alert-circle-outline',
    kind: 'notFound',
    retryable: false,
    title: '요청한 내용을 찾을 수 없어요',
  },
  conflict: {
    actionLabel: '확인',
    description: '이미 처리된 요청인지 확인해 주세요.',
    icon: 'alert-circle-outline',
    kind: 'conflict',
    retryable: false,
    title: '요청을 처리할 수 없어요',
  },
  fileTooLarge: {
    actionLabel: '확인',
    description: '파일 크기를 줄인 뒤 다시 올려 주세요.',
    icon: 'alert-circle-outline',
    kind: 'fileTooLarge',
    retryable: false,
    title: '파일이 너무 커요',
  },
  unsupportedFile: {
    actionLabel: '확인',
    description: '지원하는 파일 형식으로 다시 선택해 주세요.',
    icon: 'alert-circle-outline',
    kind: 'unsupportedFile',
    retryable: false,
    title: '지원하지 않는 파일이에요',
  },
  validation: {
    actionLabel: '확인',
    description: '입력한 내용을 다시 확인해 주세요.',
    icon: 'alert-circle-outline',
    kind: 'validation',
    retryable: false,
    title: '입력 내용을 확인해 주세요',
  },
  rateLimit: {
    actionLabel: '확인',
    description: '동일 장소의 리뷰는 한 달에 한 번만 작성할 수 있어요.',
    icon: 'time-outline',
    kind: 'rateLimit',
    retryable: false,
    title: '아직 새 리뷰를 작성할 수 없어요',
  },
  server: {
    actionLabel: '다시 시도',
    description: '서비스가 일시적으로 불안정해요. 잠시 후 다시 시도해 주세요.',
    icon: 'cloud-offline-outline',
    kind: 'server',
    retryable: true,
    title: '서버에 문제가 생겼어요',
  },
  unknown: {
    actionLabel: '다시 시도',
    description: '예상하지 못한 문제가 발생했어요. 잠시 후 다시 시도해 주세요.',
    icon: 'alert-circle-outline',
    kind: 'unknown',
    retryable: true,
    title: '요청을 완료하지 못했어요',
  },
};

/**
 * 서버가 보낸 원문 사유. **개발 중에만 쓴다.**
 *
 * 사용자 문구는 `getApiErrorMessage` 가 상태 코드로 만든다. 그런데 422 처럼
 * "무엇이 잘못됐는지"가 본문에만 있는 경우, 화면에 일반 문구만 뜨면 개발자도
 * 이유를 모른 채 추측하게 된다. `__DEV__` 에서만 함께 보여주기 위한 값이다.
 *
 * FastAPI 의 자동 검증 오류는 `detail` 이 배열이라 문자열일 때만 돌려준다.
 */
export function getApiErrorDetail(error: unknown): string | undefined {
  if (!__DEV__ || !isAxiosError(error)) return undefined;

  const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
  return typeof detail === 'string' ? detail : undefined;
}

/** docs/api의 HTTP 상태 규약과 Axios 전송 오류를 사용자 안내 문구로 변환한다. */
export function getApiErrorMessage(error: unknown): ApiErrorMessage {
  if (!isAxiosError(error)) return ERROR_MESSAGES.unknown;

  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return ERROR_MESSAGES.timeout;
  }

  if (!error.response) return ERROR_MESSAGES.network;

  const status = error.response.status;
  if (status === 400) return ERROR_MESSAGES.badRequest;
  if (status === 401) return ERROR_MESSAGES.authentication;
  if (status === 403) return ERROR_MESSAGES.permission;
  if (status === 404) return ERROR_MESSAGES.notFound;
  if (status === 409) return ERROR_MESSAGES.conflict;
  if (status === 413) return ERROR_MESSAGES.fileTooLarge;
  if (status === 415) return ERROR_MESSAGES.unsupportedFile;
  if (status === 422) return ERROR_MESSAGES.validation;
  if (status === 429) return ERROR_MESSAGES.rateLimit;
  if (status >= 500) return ERROR_MESSAGES.server;

  return ERROR_MESSAGES.unknown;
}

/**
 * 질문 전송만 SSE 라 따로 있다.
 *
 * ## 왜 `apiClient`(axios) 를 안 쓰나
 *
 * axios 는 응답을 **다 받은 뒤** 한 번에 준다. 답변을 한 글자씩 흘려보내는 것이
 * 목적이라 그걸로는 안 된다. `expo/fetch` 는 `response.body` 를 스트림으로 주므로
 * 조각이 오는 대로 읽을 수 있다.
 *
 * 그래서 `apiClient` 가 해주던 것(토큰 싣기)을 여기서 직접 한다. 대신 **401 자동
 * 재발급은 없다** — `apiClient` 의 재발급 큐를 통째로 복제해야 해서 두지 않았다.
 * 만료되면 에러로 보이고, 사용자가 다시 보낼 때 다른 요청이 먼저 갱신한다.
 */

import { fetch } from 'expo/fetch';

import { getAccessToken } from '@/src/features/auth/services/tokenStorage';

import { toChatMessage } from './chatbotAdapter';
import type { ChatMessage } from '../types/chatbot';
import type { ChatMessageResponse } from '../types/chatbotApi';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/** 스트림이 **시작되기 전** 실패. 이때는 서버가 평범한 JSON 으로 사유를 준다. */
export class ChatStreamError extends Error {
  constructor(readonly description: string) {
    super(description);
    this.name = 'ChatStreamError';
  }
}

const FALLBACK_DESCRIPTION = '답변을 받지 못했어요. 잠시 후 다시 시도해 주세요.';

type StreamHandlers = {
  /** 저장된 사용자 메시지. 임시 말풍선을 확정 id 로 바꾼다. */
  onStart: (question: ChatMessage) => void;
  /** 답변 조각. 말풍선에 이어 붙인다. */
  onDelta: (text: string) => void;
  /** 저장된 답변 메시지. 여기서 id 와 지도 핀이 확정된다. */
  onDone: (answer: ChatMessage) => void;
  /** 답변을 만들다 실패. 서버가 준 문구를 그대로 쓴다(설계 결정 E1). */
  onError: (description: string) => void;
};

type StartEvent = { event: 'start'; userMessage: ChatMessageResponse };
type DeltaEvent = { event: 'delta'; text: string };
type DoneEvent = { event: 'done'; assistantMessage: ChatMessageResponse };
type ErrorEvent = { event: 'error'; code: string; detail: string };
type StreamEvent = StartEvent | DeltaEvent | DoneEvent | ErrorEvent;

/**
 * 질문을 보내고 답변을 조각으로 받는다.
 *
 * `signal` 을 끊으면(중지 버튼) 조용히 끝난다 — `onError` 를 부르지 않는다.
 * 사용자가 일부러 멈춘 것이라 에러가 아니다. **서버는 그때까지 만든 답변을
 * 저장하지 않는다**(질문은 이미 저장돼 있다).
 */
export async function streamAnswer(
  conversationId: string,
  content: string,
  { signal, onStart, onDelta, onDone, onError }: StreamHandlers & { signal: AbortSignal },
): Promise<void> {
  let response;
  try {
    response = await fetch(`${API_URL}/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${(await getAccessToken()) ?? ''}`,
      },
      body: JSON.stringify({ content }),
      signal,
    });
  } catch {
    if (signal.aborted) return;
    throw new ChatStreamError('인터넷 연결을 확인한 뒤 다시 시도해 주세요.');
  }

  if (!response.ok) {
    throw new ChatStreamError(await readErrorDetail(response));
  }
  if (!response.body) {
    throw new ChatStreamError(FALLBACK_DESCRIPTION);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  // 조각은 이벤트 경계(`\n\n`)와 무관하게 잘려서 온다. 남은 앞부분을 들고 있다가
  // 다음 조각과 이어 붙인다 — 안 그러면 반쪽짜리 JSON 을 파싱하려다 터진다.
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() ?? '';

      for (const block of blocks) {
        const event = parseEvent(block);
        if (!event) continue;

        if (event.event === 'start') onStart(toChatMessage(event.userMessage));
        else if (event.event === 'delta') onDelta(event.text);
        else if (event.event === 'done') onDone(toChatMessage(event.assistantMessage));
        else onError(event.detail || FALLBACK_DESCRIPTION);
      }
    }
  } catch {
    // 중지 버튼으로 끊긴 것은 실패가 아니다.
    if (signal.aborted) return;
    throw new ChatStreamError(FALLBACK_DESCRIPTION);
  } finally {
    void reader.cancel().catch(() => {});
  }
}

/** `data: {...}` 한 덩어리를 이벤트로. 형식이 깨진 것은 조용히 버린다. */
function parseEvent(block: string): StreamEvent | null {
  const line = block.trim();
  if (!line.startsWith('data:')) return null;
  try {
    return JSON.parse(line.slice('data:'.length)) as StreamEvent;
  } catch {
    return null;
  }
}

/** 스트림 전 실패는 `{"detail": "..."}` 로 온다(공통 규약). */
async function readErrorDetail(response: { json: () => Promise<unknown> }): Promise<string> {
  try {
    const body = await response.json();
    const detail = (body as { detail?: unknown })?.detail;
    return typeof detail === 'string' && detail ? detail : FALLBACK_DESCRIPTION;
  } catch {
    return FALLBACK_DESCRIPTION;
  }
}

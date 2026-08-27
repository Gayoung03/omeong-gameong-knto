import { apiClient } from '@/src/services/apiClient';

import { toChatMessage, toChatMessages } from './chatbotAdapter';
import type { ChatMessage } from '../types/chatbot';
import type {
  ChatAnswerResponse,
  ChatMessageListResponse,
  ConversationCreatedResponse,
} from '../types/chatbotApi';

/**
 * 답변을 기다리는 시간.
 *
 * `apiClient` 의 기본값은 10초다. 챗봇은 장소를 검색하고 문장을 만들기까지
 * **그보다 오래 걸린다** — 서버가 전체 60초까지 기다린다(설계 결정 E2).
 * 기본값을 그대로 쓰면 서버는 멀쩡히 답을 만드는 중인데 앱만 먼저 포기한다.
 *
 * 서버보다 조금 넉넉하게 잡아 "서버가 포기한 이유"를 앱이 그대로 받게 한다.
 */
const ANSWER_TIMEOUT_MS = 65_000;

/**
 * 새 대화를 시작한다.
 *
 * **첫 질문을 보낼 때 부른다.** 챗봇 탭을 열 때마다 부르면 질문도 없는 빈
 * 대화가 쌓여 대화 개수 상한(100개)에 금방 닿는다.
 */
export async function startConversation(): Promise<string> {
  const { data } = await apiClient.post<ConversationCreatedResponse>('/chat/conversations', {});
  return data.id;
}

/**
 * 질문을 보내고 답변을 받는다. 질문과 답변 **두 개**가 돌아온다.
 *
 * 실패하면 서버는 질문도 저장하지 않는다. 화면이 질문 말풍선을 지울 필요는
 * 없지만, 재시도하면 **같은 질문이 새로 저장**된다는 뜻이다.
 */
export async function sendQuestion(
  conversationId: string,
  content: string,
): Promise<{ question: ChatMessage; answer: ChatMessage }> {
  const { data } = await apiClient.post<ChatAnswerResponse>(
    `/chat/conversations/${conversationId}/messages`,
    { content },
    { timeout: ANSWER_TIMEOUT_MS },
  );

  return {
    question: toChatMessage(data.userMessage),
    answer: toChatMessage(data.assistantMessage),
  };
}

/** 지난 대화 기록. 오래된 순으로 온다 — 채팅 화면이 위에서 아래로 읽히기 때문이다. */
export async function fetchMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessageListResponse>(
    `/chat/conversations/${conversationId}/messages`,
    { params: { limit: 50, offset: 0 } },
  );

  return toChatMessages(data.items);
}

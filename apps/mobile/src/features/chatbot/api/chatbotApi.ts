import { apiClient } from '@/src/services/apiClient';

import { toChatMessages } from './chatbotAdapter';
import type { ChatMessage } from '../types/chatbot';
import type { ChatMessageListResponse, ConversationCreatedResponse } from '../types/chatbotApi';

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

/** 지난 대화 기록. 오래된 순으로 온다 — 채팅 화면이 위에서 아래로 읽히기 때문이다. */
export async function fetchMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessageListResponse>(
    `/chat/conversations/${conversationId}/messages`,
    { params: { limit: 50, offset: 0 } },
  );

  return toChatMessages(data.items);
}

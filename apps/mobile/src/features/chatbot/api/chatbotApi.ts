import { apiClient } from '@/src/services/apiClient';

import { toChatMessages, toConversationSummary } from './chatbotAdapter';
import type { ChatMessage, ConversationSummary } from '../types/chatbot';
import type {
  ChatMessageListResponse,
  ConversationCreatedResponse,
  ConversationListResponse,
  ConversationResponse,
} from '../types/chatbotApi';

/**
 * 한 번에 받아오는 대화 수.
 *
 * **페이지네이션을 만들지 않는 이유가 여기 있다.** 서버가 한 사람당 대화를
 * 100개까지만 만들게 하고(`MAX_CONVERSATIONS`), 목록 `limit` 의 상한도 100이다.
 * 즉 한 번 부르면 항상 전부 온다. 앞으로 상한이 올라가면 그때 무한 스크롤을
 * 붙인다.
 */
const CONVERSATION_PAGE_SIZE = 100;

/** 대화를 다시 열 때 되살릴 메시지 수. */
const RESTORE_MESSAGE_LIMIT = 50;

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
 * 사이드바에 뿌릴 대화 목록. 최근에 이야기한 순이다.
 *
 * `deleted` 를 주면 **휴지통**이다 — 지운 대화가 지운 순서로 온다.
 * 응답 스키마가 같아 목록 코드를 그대로 재사용한다.
 */
export async function fetchConversations(deleted = false): Promise<ConversationSummary[]> {
  const { data } = await apiClient.get<ConversationListResponse>('/chat/conversations', {
    params: { limit: CONVERSATION_PAGE_SIZE, offset: 0, deleted },
  });

  return data.items.map(toConversationSummary);
}

/**
 * 지난 대화 기록. **응답은 언제나 오래된 순**이다 — 채팅 화면이 위에서 아래로
 * 읽히기 때문이다.
 *
 * `order=desc` 는 순서를 뒤집는 것이 아니라 **대화의 어느 쪽 끝에서 자를지**를
 * 정한다. 사용자가 대화를 다시 열었을 때 보고 싶은 것은 첫 질문이 아니라 마지막에
 * 나눈 이야기다. 기본값 `asc` 로 두면 메시지가 51개인 대화에서 가장 오래된 50개가
 * 뜨고 최근 대화가 안 보인다.
 */
export async function fetchMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessageListResponse>(
    `/chat/conversations/${conversationId}/messages`,
    { params: { limit: RESTORE_MESSAGE_LIMIT, offset: 0, order: 'desc' } },
  );

  return toChatMessages(data.items);
}

/**
 * 대화 하나. **제목을 알아내려고 부른다.**
 *
 * 사이드바에서 들어올 때는 목록이 이미 제목을 들고 있어 부를 일이 없다. 알림에서
 * 바로 들어오면(딥링크) 대화 id 하나뿐이라, 이걸 부르지 않으면 상단 바가 실제
 * 대화를 열어 놓고도 "새 대화"라고 적혀 있게 된다.
 *
 * 메시지는 오지 않는다 — 개수가 많을 수 있어 페이지네이션이 필요해서 나뉘어 있다.
 */
export async function fetchConversation(conversationId: string): Promise<ConversationSummary> {
  const { data } = await apiClient.get<ConversationResponse>(
    `/chat/conversations/${conversationId}`,
  );
  return toConversationSummary(data);
}

/**
 * 대화를 지운다. **목록에서만 사라진다** — 메시지는 한 줄도 지워지지 않고
 * 휴지통에서 되살릴 수 있다.
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/chat/conversations/${conversationId}`);
}

/**
 * 휴지통에서 되살린다.
 *
 * **목록 맨 위로 오지 않고 원래 있던 자리로 돌아간다** — 서버가 `updatedAt` 을
 * 건드리지 않는다. 지운 사이에 대화를 100개까지 새로 만들었으면 409 다.
 */
export async function restoreConversation(conversationId: string): Promise<ConversationSummary> {
  const { data } = await apiClient.post<ConversationResponse>(
    `/chat/conversations/${conversationId}/restore`,
  );
  return toConversationSummary(data);
}

/**
 * 대화 제목을 바꾼다.
 *
 * 서버가 짓는 제목은 **첫 질문 30자**라, "안녕" 같은 짧은 첫 질문이면 목록이
 * "안녕"이 된다. 그때 사용자가 직접 고칠 수 있게 열어 둔다.
 */
export async function renameConversation(
  conversationId: string,
  title: string,
): Promise<ConversationSummary> {
  const { data } = await apiClient.patch<ConversationResponse>(
    `/chat/conversations/${conversationId}`,
    { title },
  );
  return toConversationSummary(data);
}

/** 서버 응답 → 화면이 쓰는 모양. */

import { toPetPolicy } from '@/src/types/place';

import type { ChatMessage, ChatPlace, ConversationSummary } from '../types/chatbot';
import type {
  ChatMessageResponse,
  ChatPlaceResponse,
  ConversationResponse,
} from '../types/chatbotApi';

function toChatPlace(response: ChatPlaceResponse): ChatPlace {
  return {
    id: response.id,
    name: response.name,
    category: response.category,
    // 주소가 없는 장소가 있다. 지도 마커 카드에 빈 줄을 남기지 않으려고 빈 문자열로 둔다.
    address: response.address ?? '',
    imageUrl: response.primaryImageUrl,
    latitude: response.latitude,
    longitude: response.longitude,
    petPolicy: toPetPolicy(response.petPolicyType),
  };
}

export function toChatMessage(response: ChatMessageResponse): ChatMessage {
  return {
    id: response.id,
    conversationId: response.conversationId,
    role: response.role,
    content: response.content,
    referencedPlaces: response.referencedPlaces.map(toChatPlace),
  };
}

/**
 * 대화 기록을 화면 순서대로.
 *
 * **`system` 은 걸러낸다.** 저장은 될 수 있지만 사용자에게 보여줄 말이 아니다
 * (`docs/api/chatbot.md` 확정 #6).
 */
export function toChatMessages(responses: ChatMessageResponse[]): ChatMessage[] {
  return responses.filter((item) => item.role !== 'system').map(toChatMessage);
}

/**
 * 사이드바 한 줄로.
 *
 * **`routeId`·`createdAt` 은 옮기지 않는다.** 목록 줄이 그리지 않는 값이고,
 * 화면이 쓰지 않는 필드를 들고 있으면 "이건 어디서 쓰지"를 매번 확인하게 된다.
 * 필요해지면 그때 넣는다.
 */
export function toConversationSummary(response: ConversationResponse): ConversationSummary {
  return {
    id: response.id,
    title: response.title,
    preview: response.lastMessagePreview,
    messageCount: response.messageCount,
    updatedAt: response.updatedAt,
    deletedAt: response.deletedAt,
  };
}

/**
 * 서버가 내려주는 모양 그대로. `docs/api/chatbot.md` 와 1:1 이다.
 *
 * 앱에서 쓰는 모양은 `chatbot.ts` 에 따로 있고, `api/chatbotAdapter.ts` 가 옮긴다.
 * 둘을 하나로 합치면 서버 필드가 바뀔 때마다 화면 코드가 같이 흔들린다.
 */

import type { ServerPetPolicy } from '@/src/types/place';

/** 대화 목록·상세. 생성 직후 응답에는 계산값 두 개가 없다. */
export type ConversationResponse = {
  id: string;
  title: string | null;
  routeId: string | null;
  lastMessagePreview: string | null;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
};

export type ConversationCreatedResponse = {
  id: string;
  title: string | null;
  routeId: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ConversationListResponse = {
  items: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
};

/**
 * 답변이 언급한 장소.
 *
 * 장소 목록(`PlaceListItem`)보다 훨씬 좁다 — 평점·리뷰수·즐겨찾기가 없다.
 * 지도에 핀을 찍는 데 필요한 만큼만 온다.
 */
export type ChatPlaceResponse = {
  id: string;
  name: string;
  category: string;
  address: string | null;
  primaryImageUrl: string | null;
  latitude: number;
  longitude: number;
  petPolicyType: ServerPetPolicy;
};

/** `system` 도 온다. 화면에 그리지는 않지만 타입에는 있다(확정 #6). */
export type ChatMessageRole = 'user' | 'assistant' | 'system';

export type ChatMessageResponse = {
  id: string;
  conversationId: string;
  role: ChatMessageRole;
  content: string;
  referencedPlaces: ChatPlaceResponse[];
  modelName: string | null;
  createdAt: string;
};

export type ChatMessageListResponse = {
  items: ChatMessageResponse[];
  total: number;
  limit: number;
  offset: number;
};

/**
 * 질문 하나에 저장된 **두 행**.
 *
 * 명세는 이 엔드포인트를 SSE 스트림으로 정해뒀지만(`start` → `delta` → `done`)
 * 서버가 아직 JSON 으로 준다. 두 필드가 각각 `start`·`done` 이 싣는 것과 같은
 * 모양이라, 스트리밍으로 바뀌어도 **이 타입은 그대로 쓴다.**
 */
export type ChatAnswerResponse = {
  userMessage: ChatMessageResponse;
  assistantMessage: ChatMessageResponse;
};

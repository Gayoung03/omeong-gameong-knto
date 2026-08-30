/**
 * 챗봇 화면이 쓰는 모양.
 *
 * ## 2026-08-27 서버 연동으로 바뀐 것
 *
 * 확정 #6(`docs/api/chatbot.md`)에 맞춰 네 곳을 고쳤다. 예전에는 화면이 목데이터를
 * 직접 만들던 시절의 타입이라 DB 와 어긋나 있었다.
 *
 * | 예전 | 지금 | 이유 |
 * | --- | --- | --- |
 * | `id: number` | `id: string` | DB 가 UUID 문자열이다 |
 * | `text` | `content` | `chat_messages.content` |
 * | `mapPlaces` | `referencedPlaces` | `chat_messages.referenced_place_ids` |
 * | 없음 | `conversationId` | 어느 대화에 속한 메시지인지 |
 * | 2종 | `role` 3종 | `system` 도 저장될 수 있다 |
 */

import type { PetPolicy } from '@/src/types/place';

/** 화면에 그리는 것은 `user`·`assistant` 둘뿐이다. `system` 은 걸러낸다. */
export type ChatRole = 'user' | 'assistant' | 'system';

/**
 * 답변이 언급한 장소. 지도 핀과 장소 이름 줄이 이걸 그린다.
 *
 * **답변에 이름이 나온 곳만 온다.** 서버가 다섯 곳을 찾아도 답변이 세 곳만
 * 말했다면 세 곳이다(설계 결정 C4).
 */
export type ChatPlace = {
  id: string;
  name: string;
  category: string;
  /** 지도 마커 카드가 이름 아래에 그린다. */
  address: string;
  imageUrl: string | null;
  latitude: number;
  longitude: number;
  petPolicy: PetPolicy;
};

export type ChatMessage = {
  id: string;
  conversationId: string;
  role: ChatRole;
  content: string;
  referencedPlaces: ChatPlace[];
};

/**
 * 아직 서버에 저장되지 않은 말풍선.
 *
 * 질문을 보내면 답변이 올 때까지 몇 초가 걸린다. 그동안 화면이 비어 있으면
 * 사용자는 전송이 됐는지 알 수 없다. 그래서 **보낸 즉시 회색 말풍선을 띄우고**
 * 서버 응답이 오면 진짜 메시지로 바꾼다.
 *
 * `id` 가 서버 UUID 가 아니라 임시값이라 타입을 따로 둔다 — 섞이면 나중에
 * "왜 이 id 로 조회가 안 되지"가 된다.
 */
export type PendingMessage = {
  kind: 'pending';
  localId: string;
  content: string;
};

/**
 * 도착하는 중인 답변.
 *
 * 서버가 답변을 한 글자씩 흘려보내므로(SSE) 다 오기 전에도 그려야 한다.
 * `done` 을 받으면 서버 id 와 지도 핀이 확정돼 진짜 메시지로 바뀐다.
 */
export type StreamingMessage = {
  kind: 'streaming';
  localId: string;
  content: string;
};

/** 답변을 만들지 못했을 때. 질문 말풍선은 남기고 재시도 버튼을 붙인다. */
export type FailedMessage = {
  kind: 'failed';
  localId: string;
  question: string;
  description: string;
  /**
   * 질문이 서버에 저장됐는지. **말풍선을 두 번 그리지 않으려고 있다.**
   *
   * 저장됐으면(`start` 를 받았으면) 질문은 이미 제 말풍선을 갖고 있어서, 이
   * 항목은 에러만 그린다. 저장 전에 실패했으면(권한·사용량 등) 질문 말풍선이
   * 아직 없으므로 여기서 함께 그린다.
   */
  questionSaved: boolean;
};

export type ChatEntry =
  | { kind: 'message'; message: ChatMessage }
  | PendingMessage
  | StreamingMessage
  | FailedMessage;

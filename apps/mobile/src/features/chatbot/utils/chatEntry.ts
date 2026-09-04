import type { ChatEntry } from '../types/chatbot';

/** 말풍선 하나를 그릴 때 쓸 키. 서버 메시지는 UUID, 임시 말풍선은 지역 id 다. */
export function entryKey(entry: ChatEntry): string {
  return entry.kind === 'message' ? entry.message.id : entry.localId;
}

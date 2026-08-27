import { useCallback, useRef, useState } from 'react';

import { getApiErrorMessage } from '@/src/services/apiError';

import { sendQuestion, startConversation } from '../api/chatbotApi';
import type { ChatEntry } from '../types/chatbot';

/**
 * 챗봇 대화 하나를 굴린다.
 *
 * ## 대화는 첫 질문에 만들어진다
 *
 * 탭을 열 때가 아니다. 그렇게 하면 질문도 없는 빈 대화가 쌓여 대화 개수
 * 상한(100개)에 금방 닿는다(설계 결정 D2).
 *
 * ## 보낸 즉시 말풍선을 띄운다
 *
 * 답변은 장소를 검색하고 문장을 만드느라 몇 초 걸린다. 그동안 화면이 그대로면
 * 사용자는 전송이 됐는지 알 수 없어 같은 질문을 또 누른다. 그래서 회색
 * 말풍선(`pending`)을 먼저 놓고, 응답이 오면 진짜 메시지로 바꾼다.
 */
export function useChatbot() {
  const conversationId = useRef<string | null>(null);
  const nextLocalId = useRef(1);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isAnswering, setIsAnswering] = useState(false);

  const ask = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      // 답변을 기다리는 동안은 막는다. 두 질문이 겹치면 어느 답변이 어느
      // 질문의 것인지 화면에서 구분할 수 없다.
      if (!question || isAnswering) return;

      const localId = `local-${nextLocalId.current++}`;
      setEntries((current) => [...current, { kind: 'pending', localId, content: question }]);
      setIsAnswering(true);

      try {
        conversationId.current ??= await startConversation();
        const { question: saved, answer } = await sendQuestion(conversationId.current, question);

        setEntries((current) => [
          ...current.filter((entry) => entry.kind !== 'pending' || entry.localId !== localId),
          { kind: 'message', message: saved },
          { kind: 'message', message: answer },
        ]);
      } catch (error) {
        const { description } = getApiErrorMessage(error);
        setEntries((current) =>
          current.map((entry) =>
            entry.kind === 'pending' && entry.localId === localId
              ? { kind: 'failed', localId, question, description }
              : entry,
          ),
        );
      } finally {
        setIsAnswering(false);
      }
    },
    [isAnswering],
  );

  /**
   * 실패한 질문을 다시 보낸다.
   *
   * 실패하면 서버는 **질문도 저장하지 않는다.** 그래서 실패한 말풍선을 지우고
   * 처음부터 다시 보내면 된다 — 같은 질문이 두 번 저장될 걱정이 없다.
   */
  const retry = useCallback(
    (localId: string) => {
      const failed = entries.find(
        (entry): entry is Extract<ChatEntry, { kind: 'failed' }> =>
          entry.kind === 'failed' && entry.localId === localId,
      );
      if (!failed) return;

      setEntries((current) =>
        current.filter((entry) => entry.kind !== 'failed' || entry.localId !== localId),
      );
      void ask(failed.question);
    },
    [ask, entries],
  );

  return { entries, isAnswering, ask, retry };
}

/** 말풍선 하나를 그릴 때 쓸 키. 서버 메시지는 UUID, 임시 말풍선은 지역 id 다. */
export function entryKey(entry: ChatEntry): string {
  return entry.kind === 'message' ? entry.message.id : entry.localId;
}

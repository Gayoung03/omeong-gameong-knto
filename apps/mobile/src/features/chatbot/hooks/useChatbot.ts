import { useCallback, useRef, useState } from 'react';

import { startConversation } from '../api/chatbotApi';
import { ChatStreamError, streamAnswer } from '../api/chatbotStream';
import type { ChatEntry, ChatMessage } from '../types/chatbot';

const STOPPED_DESCRIPTION = '답변을 중지했어요.';
const FALLBACK_DESCRIPTION = '답변을 받지 못했어요. 잠시 후 다시 시도해 주세요.';

/** 화면을 몇 밀리초마다 갱신할지. 낮출수록 부드럽지만 리렌더가 잦아진다. */
const TYPING_TICK_MS = 50;

/**
 * 답변 전체를 대략 몇 틱에 걸쳐 그릴지. 기본값은 약 1.2초(24 × 50ms)다.
 * **키우면 느긋해지고, 줄이면 조급해진다.**
 *
 * 속도를 **전체 길이**에 맞춘다 — 짧은 답변은 한 글자씩 또박또박, 긴 답변은
 * 여러 글자씩. 그래야 길이와 상관없이 걸리는 시간이 비슷하다.
 *
 * 남은 양(`target.length - shown`)에 맞추면 안 된다. 남을수록 빨라지고 줄수록
 * 느려지는 **지수 감쇠**라 꼬리가 길게 늘어진다 — 300자가 2.6초씩 걸린다.
 */
const TYPING_TARGET_TICKS = 24;

/**
 * 챗봇 대화 하나를 굴린다.
 *
 * ## 대화는 첫 질문에 만들어진다
 *
 * 탭을 열 때가 아니다. 그렇게 하면 질문도 없는 빈 대화가 쌓여 대화 개수
 * 상한(100개)에 금방 닿는다(설계 결정 D2).
 *
 * ## 도착 속도와 표시 속도를 분리한다
 *
 * 서버 조각은 **일정한 속도로 오지 않는다.** 모델이 토큰을 묶어 보내고
 * 네트워크가 뭉치면 어절 하나가 통째로 툭 들어온다. 오는 대로 그리면
 * **네트워크 리듬이 그대로 화면 리듬이 되어** 글자가 왈칵왈칵 튀어나온다.
 *
 * 그래서 조각은 `target` 에 쌓아만 두고, 화면은 `TYPING_TICK_MS` 마다 제
 * 속도로 그것을 따라간다. 말풍선은 `pending`(서버가 아직 조용함) →
 * `streaming`(타이핑 중) → `message`(저장 완료) 순으로 바뀐다.
 *
 * ## 중지는 연결을 끊는 것이다
 *
 * `stop()` 이 `AbortController` 를 끊는다. 서버는 사용자가 멈춘 것과 네트워크가
 * 끊긴 것을 구분하지 않고, **그때까지 만든 답변을 저장하지 않는다.** 질문은
 * 이미 저장돼 있어 다시 물어볼 수 있다.
 *
 * 다만 **서버가 다 보낸 뒤(`done`) 타이핑만 남은 구간**에서는 끊을 것이 없다 —
 * 답변은 이미 저장돼 있다. 그때 중지 버튼은 `finishNow` 로 가서 **타이핑을
 * 건너뛰고 완성본을 바로 보여준다.**
 */
export function useChatbot() {
  const conversationId = useRef<string | null>(null);
  const nextLocalId = useRef(1);
  const controller = useRef<AbortController | null>(null);
  /** `done` 뒤 타이핑만 남았을 때 "지금 끝내기". 그 구간에는 끊을 연결이 없다. */
  const finishNow = useRef<(() => void) | null>(null);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isAnswering, setIsAnswering] = useState(false);

  const ask = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      // 답변을 기다리는 동안은 막는다. 두 질문이 겹치면 어느 답변이 어느
      // 질문의 것인지 화면에서 구분할 수 없다.
      if (!question || isAnswering) return;

      const localId = `local-${nextLocalId.current++}`;
      const abort = new AbortController();
      controller.current = abort;
      setEntries((current) => [...current, { kind: 'pending', localId, content: question }]);
      setIsAnswering(true);

      // `start` 를 받았는지. 받았으면 질문이 이미 제 말풍선을 갖고 있어서,
      // 실패 말풍선이 질문을 또 그리면 안 된다.
      let questionSaved = false;

      /** 임시 말풍선(`pending`·`streaming`)을 다른 것으로 바꾼다. */
      const replaceTemporary = (next: ChatEntry[]) =>
        setEntries((current) => [
          ...current.filter(
            (entry) =>
              (entry.kind !== 'pending' && entry.kind !== 'streaming') ||
              entry.localId !== localId,
          ),
          ...next,
        ]);

      /** 서버에서 받은 누적 텍스트. 화면은 이걸 제 속도로 따라간다. */
      let target = '';
      /** 화면에 반영한 글자 수. */
      let shown = 0;
      let typingTimer: ReturnType<typeof setInterval> | null = null;
      /** `done` 이 준 완성본. 타이핑이 다 끝나야 화면에 반영한다. */
      let finalAnswer: ChatMessage | null = null;

      const stopTyping = () => {
        if (typingTimer !== null) clearInterval(typingTimer);
        typingTimer = null;
      };

      /**
       * 이 질문을 끝낸다.
       *
       * **`isAnswering` 을 여기서 내린다** — 스트림이 끝나도 타이핑이 남아 있는데
       * 그때 내리면, 스크롤 애니메이션이 다시 켜져 떨리고(ChatbotScreen 의
       * `animated: !isAnswering`) 타이핑 도중에 다음 질문을 보낼 수 있게 된다.
       */
      let settled = false;
      const settle = (entry: ChatEntry) => {
        settled = true;
        stopTyping();
        replaceTemporary([entry]);
        controller.current = null;
        finishNow.current = null;
        setIsAnswering(false);
      };

      const tick = () => {
        if (shown < target.length) {
          // 전체 길이에 맞춰 속도를 낸다. 한 틱에 `step` 자를 넘지 않으므로,
          // 서버가 어절을 통째로 보내도 화면에는 나눠 그려진다.
          const step = Math.max(1, Math.ceil(target.length / TYPING_TARGET_TICKS));
          shown = Math.min(target.length, shown + step);
          const content = target.slice(0, shown);
          setEntries((current) =>
            current.map((entry) =>
              entry.kind === 'streaming' && entry.localId === localId
                ? { ...entry, content }
                : entry,
            ),
          );
        }

        // 다 따라잡았고 서버도 끝났을 때만 확정 메시지로 바꾼다. 여기서
        // 서두르면(= onDone 에서 바로 바꾸면) 못 따라간 나머지가 통째로
        // 튀어나와, 고치려던 "왈칵"이 마지막에 그대로 재현된다.
        if (finalAnswer !== null && shown >= target.length) {
          settle({ kind: 'message', message: finalAnswer });
        }
      };

      const fail = (description: string) =>
        settle({ kind: 'failed', localId, question, description, questionSaved });

      try {
        conversationId.current ??= await startConversation();

        await streamAnswer(conversationId.current, question, {
          signal: abort.signal,
          onStart: (saved) => {
            questionSaved = true;
            replaceTemporary([
              { kind: 'message', message: saved },
              { kind: 'streaming', localId, content: '' },
            ]);
          },
          onDelta: (text) => {
            target += text;
            if (typingTimer === null) typingTimer = setInterval(tick, TYPING_TICK_MS);
          },
          onDone: (answer) => {
            // 확정값을 기준으로 삼는다. 명세상 델타 누적과 같지만, 어긋나면
            // 마지막에 화면이 튄다.
            target = answer.content;
            finalAnswer = answer;
            // 여기서부터 중지 버튼은 "끊기"가 아니라 "타이핑 건너뛰기"다.
            finishNow.current = () => settle({ kind: 'message', message: answer });
            // 타이핑이 이미 끝나 있으면(조각이 없었던 경우 등) 여기서 마무리된다.
            if (typingTimer === null) tick();
          },
          onError: fail,
        });

        // 중지하면 스트림이 조용히 끝난다. 만들다 만 답변을 그대로 두면 잘린
        // 문장이 남으므로, 다시 물어볼 수 있는 모양으로 바꾼다.
        if (abort.signal.aborted) fail(STOPPED_DESCRIPTION);
      } catch (error) {
        fail(error instanceof ChatStreamError ? error.description : FALLBACK_DESCRIPTION);
      } finally {
        // 스트림이 끝났어도 **타이핑이 남아 있으면 아직 끝난 게 아니다.**
        // 그 경우 마무리는 tick 이 한다(또는 중지 버튼이 finishNow 로).
        //
        // 둘 다 아닌데 아직 안 끝났다면 이벤트를 하나도 못 받고 스트림이 닫힌
        // 것이다. 그냥 두면 `isAnswering` 이 true 로 굳어 **입력이 영영 잠긴다.**
        if (!settled && typingTimer === null) fail(FALLBACK_DESCRIPTION);
      }
    },
    [isAnswering],
  );

  /**
   * 답변 만들기를 멈춘다.
   *
   * 아직 받는 중이면 연결을 끊는다 — 서버는 그때까지 만든 답변을 저장하지 않는다.
   * 이미 다 받고 **타이핑만 남았으면 끊을 것이 없으므로**(답변은 저장됐다)
   * 타이핑을 건너뛰고 완성본을 바로 보여준다.
   */
  const stop = useCallback(() => {
    if (finishNow.current) {
      finishNow.current();
      return;
    }
    controller.current?.abort();
  }, []);

  /**
   * 실패한 질문을 다시 보낸다.
   *
   * 실패해도 **질문은 서버에 저장돼 있다**(`start` 시점에 저장된다). 그래서
   * 재시도하면 같은 질문이 한 번 더 저장된다 — 맥락으로는 자연스러운 흐름이라
   * 그대로 둔다.
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

  return { entries, isAnswering, ask, retry, stop };
}

/** 말풍선 하나를 그릴 때 쓸 키. 서버 메시지는 UUID, 임시 말풍선은 지역 id 다. */
export function entryKey(entry: ChatEntry): string {
  return entry.kind === 'message' ? entry.message.id : entry.localId;
}

import { create } from 'zustand';

import { startConversation } from '../api/chatbotApi';
import { ChatStreamError, streamAnswer } from '../api/chatbotStream';
import type { ChatEntry, ChatMessage, ChatSession } from '../types/chatbot';

const STOPPED_DESCRIPTION = '답변을 중지했어요.';
const FALLBACK_DESCRIPTION = '답변을 받지 못했어요. 잠시 후 다시 시도해 주세요.';

/** 글자 하나마다 쉬는 시간. 매번 이 범위에서 새로 뽑아 기계적인 느낌을 없앤다. */
const TYPING_CHAR_MIN_MS = 20;
const TYPING_CHAR_MAX_MS = 40;

/** 문장을 끊는 글자 **뒤에** 더 쉬는 시간. 읽는 호흡을 만든다. */
const TYPING_PAUSE_MIN_MS = 100;
const TYPING_PAUSE_MAX_MS = 200;

/** 뒤에서 쉬어 가는 글자. */
const TYPING_PAUSE_AFTER = /[.,?]/;

const randomBetween = (min: number, max: number) => min + Math.random() * (max - min);

/**
 * 진행 중인 요청의 손잡이들. **스토어 state 가 아니라 모듈 스코프 Map 이다.**
 *
 * 화면에 그리는 값이 아니고 직렬화도 안 되므로 state 에 둘 이유가 없다.
 * 대신 **창(sessionKey)마다 따로** 보관하는 것이 핵심이다 — 하나로 두면
 * B 창의 중지 버튼이 A 창의 스트림을 끊는다.
 */
const controllers = new Map<string, AbortController>();
/** `done` 뒤 타이핑만 남았을 때 "지금 끝내기". 그 구간에는 끊을 연결이 없다. */
const finishNow = new Map<string, () => void>();
/** 화면을 눌렀을 때 타이핑을 건너뛰는 함수. 타이핑 중에만 들어 있다. */
const skipTyping = new Map<string, () => void>();
/** 다음 글자를 찍을 예약. 있으면 = 타이핑 중. */
const typingTimers = new Map<string, ReturnType<typeof setTimeout>>();

let nextSessionKey = 1;
let nextLocalId = 1;

const createSession = (): ChatSession => ({
  sessionKey: `session-${nextSessionKey++}`,
  conversationId: null,
  title: null,
  entries: [],
  hydrated: false,
});

/** 창 하나에 딸린 손잡이를 전부 버린다. 창을 닫거나 로그아웃할 때. */
const forgetHandles = (sessionKey: string) => {
  const timer = typingTimers.get(sessionKey);
  if (timer !== undefined) clearTimeout(timer);
  typingTimers.delete(sessionKey);
  controllers.delete(sessionKey);
  finishNow.delete(sessionKey);
  skipTyping.delete(sessionKey);
};

type ChatSessionsState = {
  /** 열려 있는 창들. 키는 `sessionKey`(서버 대화 id 가 아니다). */
  sessions: Record<string, ChatSession>;
  /** 창이 열린 순서. 사이드바 정렬과 창 닫기 뒤 이동에 쓴다. */
  order: string[];
  /** 지금 화면에 그리는 창. **비동기 콜백에서는 절대 읽지 않는다.** */
  activeKey: string;
  /** 답변을 만드는 중인 창들. boolean 하나가 아니라 집합이다. */
  sendingKeys: string[];

  openNew: () => string;
  setActive: (sessionKey: string) => void;
  closeSession: (sessionKey: string) => void;
  ask: (sessionKey: string, question: string) => Promise<void>;
  stop: (sessionKey: string) => void;
  skip: (sessionKey: string) => void;
  retry: (sessionKey: string, localId: string) => void;
  reset: () => void;
};

const firstSession = createSession();

/**
 * 챗봇 대화창들을 굴린다. **화면이 아니라 이 모듈이 스트림의 주인이다.**
 *
 * ## 왜 화면 밖으로 꺼냈나
 *
 * 예전에는 `ChatbotScreen` 안의 `useChatbot` 이 상태를 들고 있었다. 그래서
 * **화면이 언마운트되면 스트림도 같이 죽었다** — 탭을 옮기거나 대화창을 바꾸면
 * 만들던 답변이 사라졌다. 모듈 스코프 스토어로 올리면 화면이 사라져도
 * `ask()` 의 클로저는 계속 돌고, 결과를 `sessionKey` 로 제 창에 쓴다.
 *
 * ## sessionKey 와 conversationId 를 분리한 이유
 *
 * 대화는 **첫 질문을 보낼 때** 서버에 만들어진다(설계 결정 D2 — 창을 열 때
 * 만들면 질문도 없는 빈 대화가 쌓인다). 그래서 창의 정체성을 서버 id 로 삼으면
 * 요청 도중에 키가 `draft` → UUID 로 **바뀌어야** 하고, 이미 날아간 콜백들이
 * 옛 키를 들고 남는다. 창 키는 처음부터 끝까지 고정하고 서버 id 는 세션의
 * **필드**로 둔다.
 *
 * ## 도착 속도와 표시 속도를 분리한다
 *
 * 서버 조각은 일정한 속도로 오지 않는다. 오는 대로 그리면 네트워크 리듬이
 * 그대로 화면 리듬이 되어 글자가 왈칵왈칵 튀어나온다. 그래서 조각은 `target`
 * 에 쌓아만 두고 화면은 글자 하나씩 제 속도로 따라간다. 말풍선은
 * `pending` → `streaming` → `message` 순으로 바뀐다.
 *
 * 긴 답변은 글자당 20~40ms 라 300자면 10초 안팎이다. 그래서 `skip()` 이
 * 곁들이가 아니라 **필수**다 — 화면을 누르면 건너뛴다.
 *
 * ## 중지는 연결을 끊는 것이다
 *
 * `stop()` 이 그 창의 `AbortController` 를 끊는다. 서버는 사용자가 멈춘 것과
 * 네트워크가 끊긴 것을 구분하지 않고, **그때까지 만든 답변을 저장하지 않는다.**
 * 질문은 이미 저장돼 있어 다시 물어볼 수 있다.
 *
 * 다만 서버가 다 보낸 뒤(`done`) 타이핑만 남은 구간에서는 끊을 것이 없다 —
 * 답변은 이미 저장됐다. 그때 중지 버튼은 `finishNow` 로 가서 타이핑을
 * 건너뛰고 완성본을 바로 보여준다.
 */
export const useChatSessionsStore = create<ChatSessionsState>((set, get) => {
  /**
   * 세션 하나의 필드를 바꾼다.
   *
   * **없는 세션이면 아무 일도 하지 않는다.** 창을 닫은 뒤에 도착한 콜백이
   * 지워진 창을 되살리면 안 된다.
   */
  const patchSession = (sessionKey: string, patch: Partial<ChatSession>) =>
    set((state) => {
      const session = state.sessions[sessionKey];
      if (!session) return state;
      return { sessions: { ...state.sessions, [sessionKey]: { ...session, ...patch } } };
    });

  const patchEntries = (sessionKey: string, update: (entries: ChatEntry[]) => ChatEntry[]) =>
    set((state) => {
      const session = state.sessions[sessionKey];
      if (!session) return state;
      return {
        sessions: {
          ...state.sessions,
          [sessionKey]: { ...session, entries: update(session.entries) },
        },
      };
    });

  const markSending = (sessionKey: string, sending: boolean) =>
    set((state) => ({
      sendingKeys: sending
        ? state.sendingKeys.includes(sessionKey)
          ? state.sendingKeys
          : [...state.sendingKeys, sessionKey]
        : state.sendingKeys.filter((key) => key !== sessionKey),
    }));

  return {
    sessions: { [firstSession.sessionKey]: firstSession },
    order: [firstSession.sessionKey],
    activeKey: firstSession.sessionKey,
    sendingKeys: [],

    openNew: () => {
      const session = createSession();
      set((state) => ({
        sessions: { ...state.sessions, [session.sessionKey]: session },
        order: [...state.order, session.sessionKey],
        activeKey: session.sessionKey,
      }));
      return session.sessionKey;
    },

    setActive: (sessionKey) => {
      if (!get().sessions[sessionKey]) return;
      set({ activeKey: sessionKey });
    },

    /**
     * 창을 닫는다. 답변을 만드는 중이었으면 끊는다.
     *
     * **창이 하나도 없는 상태는 만들지 않는다.** 화면이 그릴 것이 없어져
     * `activeKey` 를 null 로 다뤄야 하는데, 그 상태가 사용자에게 보이는 일은
     * 없다(마지막 창을 닫으면 빈 새 창이 그 자리를 받는다).
     */
    closeSession: (sessionKey) => {
      controllers.get(sessionKey)?.abort();
      forgetHandles(sessionKey);
      set((state) => {
        if (!state.sessions[sessionKey]) return state;

        const sessions = { ...state.sessions };
        delete sessions[sessionKey];
        const order = state.order.filter((key) => key !== sessionKey);
        const sendingKeys = state.sendingKeys.filter((key) => key !== sessionKey);

        const fallback = order[order.length - 1];
        if (fallback === undefined) {
          const fresh = createSession();
          return {
            sessions: { [fresh.sessionKey]: fresh },
            order: [fresh.sessionKey],
            activeKey: fresh.sessionKey,
            sendingKeys,
          };
        }

        return {
          sessions,
          order,
          activeKey: state.activeKey === sessionKey ? fallback : state.activeKey,
          sendingKeys,
        };
      });
    },

    /**
     * 질문을 보내고 답변을 받는다.
     *
     * **첫 인자 `sessionKey` 가 이 요청의 대상이다.** 아래 콜백들은 전부 이
     * 클로저 변수만 쓴다 — `get().activeKey` 를 읽으면 사용자가 그 사이에 창을
     * 바꿨을 때 답변이 엉뚱한 창에 쓰인다.
     */
    ask: async (sessionKey, rawQuestion) => {
      const question = rawQuestion.trim();
      const session = get().sessions[sessionKey];
      // 그 창이 답변을 기다리는 동안은 막는다. 두 질문이 겹치면 어느 답변이
      // 어느 질문의 것인지 화면에서 구분할 수 없다. **다른 창은 막지 않는다.**
      if (!question || !session || get().sendingKeys.includes(sessionKey)) return;

      const localId = `local-${nextLocalId++}`;
      const abort = new AbortController();
      controllers.set(sessionKey, abort);
      patchEntries(sessionKey, (entries) => [
        ...entries,
        { kind: 'pending', localId, content: question },
      ]);
      markSending(sessionKey, true);

      // `start` 를 받았는지. 받았으면 질문이 이미 제 말풍선을 갖고 있어서,
      // 실패 말풍선이 질문을 또 그리면 안 된다.
      let questionSaved = false;

      /** 임시 말풍선(`pending`·`streaming`)을 다른 것으로 바꾼다. */
      const replaceTemporary = (next: ChatEntry[]) =>
        patchEntries(sessionKey, (entries) => [
          ...entries.filter(
            (entry) =>
              (entry.kind !== 'pending' && entry.kind !== 'streaming') || entry.localId !== localId,
          ),
          ...next,
        ]);

      /** 서버에서 받은 누적 텍스트. 화면은 이걸 제 속도로 따라간다. */
      let target = '';
      /** 화면에 반영한 글자 수. */
      let shown = 0;
      /** `done` 이 준 완성본. 타이핑이 다 끝나야 화면에 반영한다. */
      let finalAnswer: ChatMessage | null = null;
      /** 사용자가 건너뛰었는지. 한 번 누르면 이후 조각도 타이핑 없이 바로 보여준다. */
      let skipped = false;

      const isTyping = () => typingTimers.has(sessionKey);

      const stopTyping = () => {
        const timer = typingTimers.get(sessionKey);
        if (timer !== undefined) clearTimeout(timer);
        typingTimers.delete(sessionKey);
      };

      const showUpTo = (count: number) => {
        shown = count;
        const content = target.slice(0, shown);
        patchEntries(sessionKey, (entries) =>
          entries.map((entry) =>
            entry.kind === 'streaming' && entry.localId === localId ? { ...entry, content } : entry,
          ),
        );
      };

      /**
       * 이 질문을 끝낸다.
       *
       * **`sendingKeys` 에서 여기서 뺀다** — 스트림이 끝나도 타이핑이 남아
       * 있는데 그때 빼면, 스크롤 애니메이션이 다시 켜져 떨리고(ChatbotScreen 의
       * `animated: !isAnswering`) 타이핑 도중에 다음 질문을 보낼 수 있게 된다.
       */
      let settled = false;
      const settle = (entry: ChatEntry) => {
        settled = true;
        stopTyping();
        replaceTemporary([entry]);
        controllers.delete(sessionKey);
        finishNow.delete(sessionKey);
        skipTyping.delete(sessionKey);
        markSending(sessionKey, false);
      };

      /** 다음 글자까지 쉴 시간. **방금 찍은 글자**를 보고 정한다 — 부호는 찍고 나서 쉰다. */
      const nextDelay = () => {
        const justTyped = target[shown - 1] ?? '';
        const pause = TYPING_PAUSE_AFTER.test(justTyped)
          ? randomBetween(TYPING_PAUSE_MIN_MS, TYPING_PAUSE_MAX_MS)
          : 0;
        return randomBetween(TYPING_CHAR_MIN_MS, TYPING_CHAR_MAX_MS) + pause;
      };

      /** 글자 하나를 그리고 다음 호출을 예약한다. */
      const typeOne = () => {
        typingTimers.delete(sessionKey);

        if (shown >= target.length) {
          // 서버가 더 보낼 게 있으면 onDelta 가 깨운다. 여기서 멈춰 둔다.
          //
          // 다 따라잡았고 서버도 끝났을 때만 확정 메시지로 바꾼다. 여기서
          // 서두르면(= onDone 에서 바로 바꾸면) 못 따라간 나머지가 통째로
          // 튀어나와, 없애려던 "왈칵"이 마지막에 그대로 재현된다.
          if (finalAnswer !== null) settle({ kind: 'message', message: finalAnswer });
          return;
        }

        // 이모지는 UTF-16 두 칸을 차지한다. 한 칸씩 자르면 반쪽짜리 깨진
        // 문자가 화면에 보인다.
        const code = target.charCodeAt(shown);
        const width = code >= 0xd800 && code <= 0xdbff ? 2 : 1;
        showUpTo(Math.min(target.length, shown + width));

        typingTimers.set(sessionKey, setTimeout(typeOne, nextDelay()));
      };

      /**
       * 타이핑을 건너뛰고 **받은 데까지 즉시** 보여준다.
       *
       * 한 번 누르면 `skipped` 로 남아 이후 조각도 기다리지 않는다 — 사용자가
       * "빨리 보고 싶다"고 밝힌 것을 되돌리지 않는다.
       */
      const skip = () => {
        skipped = true;
        stopTyping();
        showUpTo(target.length);
        if (finalAnswer !== null) settle({ kind: 'message', message: finalAnswer });
      };

      const fail = (description: string) =>
        settle({ kind: 'failed', localId, question, description, questionSaved });

      try {
        // **여기서 딱 한 번 확보한다.** 이후 콜백은 sessionKey 만 본다.
        let conversationId = get().sessions[sessionKey]?.conversationId ?? null;
        if (conversationId === null) {
          conversationId = await startConversation();
          patchSession(sessionKey, { conversationId });
        }

        await streamAnswer(conversationId, question, {
          signal: abort.signal,
          onStart: (saved) => {
            questionSaved = true;
            // 화면을 누르면 건너뛸 수 있게 여기서부터 열어 둔다.
            skipTyping.set(sessionKey, skip);
            replaceTemporary([
              { kind: 'message', message: saved },
              { kind: 'streaming', localId, content: '' },
            ]);
          },
          onDelta: (text) => {
            target += text;
            // 이미 건너뛴 뒤라면 기다리지 않는다.
            if (skipped) {
              showUpTo(target.length);
              return;
            }
            // 쉬고 있던 타이머를 깨운다.
            if (!isTyping()) typeOne();
          },
          onDone: (answer) => {
            // 확정값을 기준으로 삼는다. 명세상 델타 누적과 같지만, 어긋나면
            // 마지막에 화면이 튄다.
            target = answer.content;
            finalAnswer = answer;
            // 여기서부터 중지 버튼은 "끊기"가 아니라 "타이핑 건너뛰기"다.
            finishNow.set(sessionKey, skip);
            // 타이핑이 이미 끝나 있으면(건너뛰었거나 조각이 없었으면) 여기서 마무리된다.
            if (!isTyping()) typeOne();
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
        // 그 경우 마무리는 typeOne 이 한다(또는 중지 버튼이 finishNow 로).
        //
        // 둘 다 아닌데 아직 안 끝났다면 이벤트를 하나도 못 받고 스트림이 닫힌
        // 것이다. 그냥 두면 이 창이 sendingKeys 에 남아 **입력이 영영 잠긴다.**
        if (!settled && !isTyping()) fail(FALLBACK_DESCRIPTION);
      }
    },

    /**
     * 그 창의 답변 만들기를 멈춘다. **다른 창은 계속 돈다.**
     *
     * 아직 받는 중이면 연결을 끊는다 — 서버는 그때까지 만든 답변을 저장하지 않는다.
     * 이미 다 받고 타이핑만 남았으면 끊을 것이 없으므로(답변은 저장됐다)
     * 타이핑을 건너뛰고 완성본을 바로 보여준다.
     */
    stop: (sessionKey) => {
      const finish = finishNow.get(sessionKey);
      if (finish) {
        finish();
        return;
      }
      controllers.get(sessionKey)?.abort();
    },

    /**
     * 타이핑을 건너뛰고 지금까지 받은 것을 한 번에 보여준다.
     *
     * 화면을 누르면 불린다. 타이핑 중이 아니면 아무 일도 하지 않아 평소 터치를
     * 방해하지 않는다.
     */
    skip: (sessionKey) => {
      skipTyping.get(sessionKey)?.();
    },

    /**
     * 실패한 질문을 다시 보낸다.
     *
     * 실패해도 **질문은 서버에 저장돼 있다**(`start` 시점에 저장된다). 그래서
     * 재시도하면 같은 질문이 한 번 더 저장된다 — 맥락으로는 자연스러운 흐름이라
     * 그대로 둔다.
     */
    retry: (sessionKey, localId) => {
      const session = get().sessions[sessionKey];
      if (!session) return;

      const failed = session.entries.find(
        (entry): entry is Extract<ChatEntry, { kind: 'failed' }> =>
          entry.kind === 'failed' && entry.localId === localId,
      );
      if (!failed) return;

      patchEntries(sessionKey, (entries) =>
        entries.filter((entry) => entry.kind !== 'failed' || entry.localId !== localId),
      );
      void get().ask(sessionKey, failed.question);
    },

    /**
     * 창·스트림·손잡이를 전부 버리고 빈 창 하나로 되돌린다.
     *
     * **로그아웃에 연결할 자리다**(5단계). 정리하지 않으면 다음 계정 화면에
     * 이전 사용자의 대화가 그대로 남는다.
     */
    reset: () => {
      for (const sessionKey of get().order) {
        controllers.get(sessionKey)?.abort();
        forgetHandles(sessionKey);
      }
      const fresh = createSession();
      set({
        sessions: { [fresh.sessionKey]: fresh },
        order: [fresh.sessionKey],
        activeKey: fresh.sessionKey,
        sendingKeys: [],
      });
    },
  };
});

/** 창이 비어 있을 때 매번 새 배열을 만들면 그때마다 리렌더된다. */
const EMPTY_ENTRIES: ChatEntry[] = [];

/** 지금 보고 있는 창의 말풍선들. */
export const useActiveEntries = () =>
  useChatSessionsStore((state) => state.sessions[state.activeKey]?.entries ?? EMPTY_ENTRIES);

/** 그 창이 답변을 만드는 중인지. **다른 창의 상태에 영향받지 않는다.** */
export const useIsAnswering = (sessionKey: string) =>
  useChatSessionsStore((state) => state.sendingKeys.includes(sessionKey));

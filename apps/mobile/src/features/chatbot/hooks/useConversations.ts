import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  deleteConversation,
  fetchConversations,
  renameConversation,
  restoreConversation,
} from '../api/chatbotApi';
import { useChatSessionsStore } from '../stores/useChatSessionsStore';
import type { ConversationSummary } from '../types/chatbot';
import { conversationsQueryKey, conversationsQueryPrefix } from './conversationKeys';

/**
 * 사이드바에 뿌릴 서버 대화 목록.
 *
 * **열린 창(Zustand)과 역할을 섞지 않는다.** 이쪽은 "서버에 무엇이 저장돼
 * 있나"이고, 스토어는 "지금 무엇을 열어 놓고 있나"다. 둘을 한 곳에 합치면
 * 답변을 만드는 중인 창을 목록이 다시 불러와 덮어쓰는 사고가 난다.
 */
export function useConversations() {
  return useQuery<ConversationSummary[]>({
    queryKey: conversationsQueryKey(),
    queryFn: () => fetchConversations(false),
  });
}

/**
 * 휴지통.
 *
 * `enabled` 로 **시트를 열었을 때만** 부른다. 사이드바를 열 때마다 같이 부르면
 * 대부분의 사용자가 보지도 않을 목록을 매번 받아온다.
 */
export function useTrashedConversations(enabled: boolean) {
  return useQuery<ConversationSummary[]>({
    queryKey: conversationsQueryKey(true),
    queryFn: () => fetchConversations(true),
    enabled,
  });
}

/**
 * 대화를 지운다.
 *
 * 서버에서는 목록에서만 사라지고 메시지는 남는다. 앱에서는 그 대화를 **열어둔
 * 창도 함께 닫는다** — 남겨두면 목록에 없는 대화를 화면에서 계속 보게 되고,
 * 거기에 질문을 보내면 서버가 404 로 거절한다.
 */
export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const closeByConversationId = useChatSessionsStore((state) => state.closeByConversationId);

  return useMutation({
    mutationFn: (conversationId: string) => deleteConversation(conversationId),
    onSuccess: (_, conversationId) => {
      closeByConversationId(conversationId);
      void queryClient.invalidateQueries({ queryKey: conversationsQueryPrefix });
    },
  });
}

/**
 * 휴지통에서 되살린다.
 *
 * 살아 있는 대화가 이미 100개면 서버가 409 로 거절한다 — 지워서 자리를 냈다가
 * 복구로 상한을 넘기는 것을 막기 위해서다. 화면이 그 메시지를 그대로 보여준다.
 */
export function useRestoreConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => restoreConversation(conversationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: conversationsQueryPrefix });
    },
  });
}

/** 대화 제목을 바꾼다. 열려 있는 창의 제목도 함께 맞춘다. */
export function useRenameConversation() {
  const queryClient = useQueryClient();
  const renameSession = useChatSessionsStore((state) => state.renameSession);

  return useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      renameConversation(conversationId, title),
    onSuccess: (updated) => {
      // PATCH 는 빈 제목을 거부하므로 `title` 은 항상 값이 있다. 타입만 넓다.
      if (updated.title !== null) renameSession(updated.id, updated.title);
      void queryClient.invalidateQueries({ queryKey: conversationsQueryPrefix });
    },
  });
}

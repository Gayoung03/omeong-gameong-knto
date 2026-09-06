import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

import { ConversationRow } from './ConversationRow';
import { ConversationTrashPanel } from './ConversationTrashPanel';
import { useConversations, useDeleteConversation } from '../hooks/useConversations';
import { useChatSessionsStore } from '../stores/useChatSessionsStore';
import type { ConversationSummary } from '../types/chatbot';

const MAX_PANEL_WIDTH = 320;
const PANEL_WIDTH_RATIO = 0.86;
const SLIDE_MS = 200;

type Props = {
  onClose: () => void;
  /** 이름 바꾸기 창은 **화면이 띄운다.** 아래 주석 참고. */
  onRequestRename: (conversation: ConversationSummary) => void;
  visible: boolean;
};

/**
 * 저장된 대화 목록. 창을 바꾸는 **유일한 수단**이다(설계 결정 C-1 — 상단 탭 줄은 없다).
 *
 * ## 이름 바꾸기 창을 여기서 띄우지 않는 이유
 *
 * 이 서랍이 RN `Modal` 이라, 그 위에 또 `Modal` 을 겹치면 플랫폼마다 층 순서가
 * 다르게 나온다. 이름 바꾸기는 `ChatbotScreen` 이 **형제로** 띄우고 여기서는
 * 요청만 올린다. 서랍은 열린 채로 남아 어느 대화를 고쳤는지 계속 보인다.
 *
 * ## 삭제에 확인 창이 없다
 *
 * 지우기가 되돌릴 수 있는 동작이기 때문이다 — 대화는 휴지통으로 가고 메시지는
 * 한 줄도 사라지지 않는다. 확인 창은 되돌릴 수 없는 동작에 쓰는 무게라, 여기서는
 * 대신 목록 맨 아래에 휴지통을 늘 보이게 뒀다.
 */
export function ConversationSidebar({ onClose, onRequestRename, visible }: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onClose}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      {/* 열 때마다 새로 그려야 휴지통을 보다 닫았을 때 목록으로 돌아온다. */}
      {visible ? <SidebarPanel onClose={onClose} onRequestRename={onRequestRename} /> : null}
    </Modal>
  );
}

function SidebarPanel({ onClose, onRequestRename }: Omit<Props, 'visible'>) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const panelWidth = Math.min(MAX_PANEL_WIDTH, width * PANEL_WIDTH_RATIO);

  const [mode, setMode] = useState<'list' | 'trash'>('list');

  /**
   * 서랍이 왼쪽에서 밀려 나오는 값.
   *
   * **`useRef` 가 아니라 `useState` 의 지연 초기화로 만든다.** 값이 한 번만
   * 만들어지고 바뀌지 않는다는 점은 같지만, `useRef(...).current` 를 렌더 중에
   * 읽으면 `react-hooks/refs` 가 막는다(아래 `interpolate` 가 렌더 중 호출이다).
   * ref 는 "렌더에 필요 없는 값"이라는 규칙이라, 화면을 그리는 데 쓰는 값은
   * 애초에 ref 에 두면 안 된다는 뜻이다.
   */
  const [slide] = useState(() => new Animated.Value(0));
  useEffect(() => {
    Animated.timing(slide, { duration: SLIDE_MS, toValue: 1, useNativeDriver: true }).start();
  }, [slide]);

  const { data, isPending, isError, refetch } = useConversations();
  const remove = useDeleteConversation();

  const openExisting = useChatSessionsStore((state) => state.openExisting);
  const openNew = useChatSessionsStore((state) => state.openNew);
  const sessions = useChatSessionsStore((state) => state.sessions);
  const sendingKeys = useChatSessionsStore((state) => state.sendingKeys);
  const activeConversationId = useChatSessionsStore(
    (state) => state.sessions[state.activeKey]?.conversationId ?? null,
  );

  /**
   * 지금 답변을 만드는 중인 **대화 id** 들.
   *
   * 스토어는 창 키로 들고 있어서 목록(서버 대화)과 맞대려면 한 번 옮겨야 한다.
   * 선택자 안에서 만들면 매번 새 배열이 나와 무한 리렌더가 된다 — 그래서 두
   * 원본을 각각 구독하고 여기서 합친다.
   */
  const answeringIds = useMemo(() => {
    const ids = sendingKeys
      .map((key) => sessions[key]?.conversationId)
      .filter((id): id is string => typeof id === 'string');
    return new Set(ids);
  }, [sendingKeys, sessions]);

  const conversations = data ?? [];

  const handleSelect = (conversation: ConversationSummary) => {
    openExisting(conversation.id, conversation.title);
    onClose();
  };

  const handleNew = () => {
    openNew();
    onClose();
  };

  const renderList = () => {
    if (isPending) {
      return (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      );
    }

    if (isError) {
      return (
        <View style={styles.center}>
          <Text style={styles.errorText}>대화 목록을 불러오지 못했어요.</Text>
          <Pressable
            accessibilityRole="button"
            onPress={() => void refetch()}
            style={({ pressed }) => [styles.retryButton, pressed && styles.pressed]}
          >
            <Text style={styles.retryLabel}>다시 시도</Text>
          </Pressable>
        </View>
      );
    }

    if (conversations.length === 0) {
      return (
        <EmptyState
          description={'혼디에게 처음 질문을 보내면\n여기에 쌓이기 시작해요.'}
          icon="chatbubbles-outline"
          title="아직 대화가 없어요"
        />
      );
    }

    return conversations.map((conversation) => (
      <ConversationRow
        conversation={conversation}
        isActive={conversation.id === activeConversationId}
        isAnswering={answeringIds.has(conversation.id)}
        key={conversation.id}
        onDelete={() => remove.mutate(conversation.id)}
        onPress={() => handleSelect(conversation)}
        onRename={() => onRequestRename(conversation)}
      />
    ));
  };

  return (
    <View style={styles.overlay}>
      <Pressable
        accessibilityLabel="대화 목록 닫기"
        accessibilityRole="button"
        onPress={onClose}
        style={styles.backdrop}
      />
      <Animated.View
        accessibilityViewIsModal
        style={[
          styles.panel,
          shadow.sm,
          {
            paddingBottom: Math.max(insets.bottom, spacing.sm),
            paddingTop: Math.max(insets.top, spacing.sm),
            transform: [
              {
                translateX: slide.interpolate({
                  inputRange: [0, 1],
                  outputRange: [-panelWidth, 0],
                }),
              },
            ],
            width: panelWidth,
          },
        ]}
      >
        {mode === 'trash' ? (
          <ConversationTrashPanel onBack={() => setMode('list')} />
        ) : (
          <>
            <View style={styles.header}>
              <Text style={styles.heading}>대화 목록</Text>
              <Pressable
                accessibilityLabel="닫기"
                accessibilityRole="button"
                hitSlop={10}
                onPress={onClose}
                style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}
              >
                <Ionicons color={colors.iconGray} name="close" size={20} />
              </Pressable>
            </View>

            <Pressable
              accessibilityLabel="새 대화 시작"
              accessibilityRole="button"
              onPress={handleNew}
              style={({ pressed }) => [styles.newButton, pressed && styles.pressed]}
            >
              <Ionicons color={colors.surface} name="add" size={17} />
              <Text style={styles.newLabel}>새 대화</Text>
            </Pressable>

            <ScrollView
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
              style={styles.list}
            >
              {renderList()}
            </ScrollView>

            {/*
              휴지통은 파괴적 동작이 아니라 **되돌리는** 곳이지만, 평소에 볼 일이
              없는 줄이라 회색 작은 글씨로 시각적 무게를 낮춘다.
            */}
            <Pressable
              accessibilityLabel="휴지통 열기"
              accessibilityRole="button"
              onPress={() => setMode('trash')}
              style={({ pressed }) => [styles.trashRow, pressed && styles.pressed]}
            >
              <Ionicons color={colors.textTertiary} name="trash-outline" size={16} />
              <Text style={styles.trashLabel}>휴지통</Text>
            </Pressable>
          </>
        )}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  center: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  closeButton: {
    alignItems: 'center',
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  errorText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 48,
    paddingHorizontal: spacing.md,
  },
  heading: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '700',
  },
  list: {
    // 목록이 남는 높이를 차지해야 맨 아래 휴지통 줄이 화면 밖으로 밀리지 않는다.
    flex: 1,
  },
  listContent: {
    flexGrow: 1,
    paddingBottom: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  newButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: 6,
    justifyContent: 'center',
    marginBottom: spacing.sm,
    marginHorizontal: spacing.md,
    minHeight: 42,
  },
  newLabel: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  overlay: {
    backgroundColor: overlayColors.dim,
    flex: 1,
    flexDirection: 'row',
  },
  panel: {
    backgroundColor: colors.surface,
    borderBottomRightRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    // 너비는 화면 크기에 맞춰 인라인으로 준다. 세로는 부모(row)의 stretch 로 꽉 찬다.
    maxWidth: MAX_PANEL_WIDTH,
  },
  pressed: {
    opacity: 0.68,
  },
  retryButton: {
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  retryLabel: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  trashLabel: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  trashRow: {
    alignItems: 'center',
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: 6,
    minHeight: 44,
    paddingHorizontal: spacing.md,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { colors, radius, spacing, typography } from '@/src/theme';
import { relativeTime } from '@/src/utils/relativeTime';

import { UNTITLED_CONVERSATION } from './ConversationRow';
import { useRestoreConversation, useTrashedConversations } from '../hooks/useConversations';
import { conversationErrorText } from '../utils/conversationError';

type Props = {
  onBack: () => void;
};

/**
 * 휴지통. **사이드바를 덮는 화면으로 만들었다.**
 *
 * 설계안은 바텀시트였는데, 사이드바가 RN `Modal` 이라 `@gorhom/bottom-sheet` 가
 * 그 아래에 깔린다(시트는 화면 루트의 `BottomSheetModalProvider` 에 그려진다).
 * 서랍 안에서 화면을 바꾸면 그 문제가 통째로 사라지고, "목록 → 휴지통 → 뒤로"가
 * 서랍 하나 안에서 끝나 오가기도 짧다.
 *
 * **영구 삭제 버튼은 없다.** 요건이 "지워도 데이터는 남는다"이고 설계 결정 D3 이
 * "지우지 않음"이라, 휴지통은 쌓이기만 하는 것이 의도된 동작이다.
 */
export function ConversationTrashPanel({ onBack }: Props) {
  const { data, isPending, isError } = useTrashedConversations(true);
  const restore = useRestoreConversation();

  const conversations = data ?? [];

  const renderBody = () => {
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
          <Text style={styles.errorText}>휴지통을 불러오지 못했어요.</Text>
        </View>
      );
    }

    if (conversations.length === 0) {
      return (
        <EmptyState
          description={'지운 대화가 여기 모여요.\n언제든 되살릴 수 있어요.'}
          icon="trash-outline"
          title="휴지통이 비어 있어요"
        />
      );
    }

    return conversations.map((conversation) => (
      <View key={conversation.id} style={styles.row}>
        <View style={styles.rowText}>
          <Text numberOfLines={1} style={styles.title}>
            {conversation.title ?? UNTITLED_CONVERSATION}
          </Text>
          <Text style={styles.deletedAt}>
            {/* deletedAt 은 휴지통에서만 값이 있다. 없으면 시각을 지어내지 않는다. */}
            {conversation.deletedAt === null
              ? '삭제됨'
              : `${relativeTime(conversation.deletedAt)} 삭제`}
          </Text>
        </View>
        <Pressable
          accessibilityLabel={`${conversation.title ?? UNTITLED_CONVERSATION} 복구`}
          accessibilityRole="button"
          disabled={restore.isPending}
          onPress={() => restore.mutate(conversation.id)}
          style={({ pressed }) => [
            styles.restoreButton,
            restore.isPending && styles.restoreButtonBusy,
            pressed && styles.pressed,
          ]}
        >
          <Text style={styles.restoreLabel}>복구</Text>
        </Pressable>
      </View>
    ));
  };

  return (
    <View style={styles.panel}>
      <View style={styles.header}>
        <Pressable
          accessibilityLabel="대화 목록으로 돌아가기"
          accessibilityRole="button"
          hitSlop={10}
          onPress={onBack}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
        >
          <Ionicons color={colors.textPrimary} name="chevron-back" size={20} />
        </Pressable>
        <Text style={styles.heading}>휴지통</Text>
      </View>

      {/* 복구는 살아 있는 대화가 100개면 거절된다. 서버가 준 안내를 그대로 보여준다. */}
      {restore.isError ? (
        <Text style={styles.errorBanner}>{conversationErrorText(restore.error)}</Text>
      ) : null}

      <ScrollView
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        style={styles.list}
      >
        {renderBody()}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  backButton: {
    alignItems: 'center',
    height: 32,
    justifyContent: 'center',
    marginLeft: -spacing.xs,
    width: 32,
  },
  center: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  deletedAt: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: 3,
  },
  errorBanner: {
    backgroundColor: colors.errorBg,
    borderRadius: radius.sm,
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
    marginBottom: spacing.sm,
    marginHorizontal: spacing.md,
    padding: spacing.sm,
  },
  errorText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
    minHeight: 48,
    paddingHorizontal: spacing.md,
  },
  heading: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '700',
  },
  list: {
    flex: 1,
  },
  listContent: {
    flexGrow: 1,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.sm,
  },
  panel: {
    flex: 1,
  },
  pressed: {
    opacity: 0.68,
  },
  restoreButton: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    justifyContent: 'center',
    minHeight: 32,
    paddingHorizontal: spacing.md,
  },
  restoreButtonBusy: {
    opacity: 0.6,
  },
  restoreLabel: {
    color: colors.primaryDeep,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    minHeight: 56,
    paddingHorizontal: spacing.sm,
  },
  rowText: {
    flex: 1,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
});

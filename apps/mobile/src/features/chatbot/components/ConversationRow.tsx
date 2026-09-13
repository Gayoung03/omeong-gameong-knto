import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';
import { relativeTime } from '@/src/utils/relativeTime';

import type { ConversationSummary } from '../types/chatbot';

/** 서버가 제목을 짓기 전(질문 한 번도 없는 대화)에 보여줄 이름. */
export const UNTITLED_CONVERSATION = '새 대화';

type Props = {
  conversation: ConversationSummary;
  /** 지금 화면에 열려 있는 대화인지. */
  isActive: boolean;
  /** 이 대화가 지금 답변을 만드는 중인지. 요건 2가 사용자 눈에 보이는 자리다. */
  isAnswering: boolean;
  onDelete: () => void;
  onPress: () => void;
  onRename: () => void;
};

/**
 * 사이드바 한 줄.
 *
 * ## 버튼을 Pressable 안에 넣지 않는다
 *
 * 웹에서 `<button>` 이 중첩되면 안쪽 버튼이 눌리지 않는다. 그래서 줄 전체를
 * 덮는 Pressable 과 오른쪽 삭제 버튼을 **형제**로 두고 겹쳐 놓았다
 * (줄 안쪽에 오른쪽 여백을 줘서 글자가 아이콘 밑으로 들어가지 않는다).
 *
 * ## 진행 중 점
 *
 * 창 전환 수단이 사이드바뿐이라(설계 결정 C-1) **"B에서 질문하는 동안 A도
 * 돌고 있다"를 사용자가 알 수 있는 곳이 여기 하나뿐이다.**
 */
export function ConversationRow({
  conversation,
  isActive,
  isAnswering,
  onDelete,
  onPress,
}: Props) {
  const title = conversation.title ?? UNTITLED_CONVERSATION;

  return (
    <View style={styles.wrapper}>
      <Pressable
        accessibilityLabel={`${title} 대화 열기`}
        accessibilityRole="button"
        accessibilityState={{ selected: isActive }}
        onPress={onPress}
        style={({ pressed }) => [
          styles.row,
          isActive && styles.rowActive,
          pressed && styles.pressed,
        ]}
      >
        <View style={styles.titleLine}>
          {isAnswering ? (
            <View accessibilityLabel="답변 생성 중" style={styles.answeringDot} />
          ) : null}
          <Text numberOfLines={1} style={[styles.title, isActive && styles.titleActive]}>
            {title}
          </Text>
        </View>
        <View style={styles.previewLine}>
          <Text numberOfLines={1} style={styles.preview}>
            {conversation.preview ?? '아직 주고받은 말이 없어요'}
          </Text>
          <Text numberOfLines={1} style={styles.time}>
            {relativeTime(conversation.updatedAt)}
          </Text>
        </View>
      </Pressable>

      <View style={styles.actions}>
        <Pressable
          accessibilityHint="휴지통으로 옮깁니다. 대화 내용은 지워지지 않아요"
          accessibilityLabel={`${title} 삭제`}
          accessibilityRole="button"
          hitSlop={8}
          onPress={onDelete}
          style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
        >
          <Ionicons color={colors.iconGray} name="trash-outline" size={15} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
    position: 'absolute',
    right: spacing.sm,
    top: spacing.sm,
  },
  answeringDot: {
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: 7,
    width: 7,
  },
  iconButton: {
    alignItems: 'center',
    height: 26,
    justifyContent: 'center',
    width: 26,
  },
  pressed: {
    opacity: 0.68,
  },
  preview: {
    color: colors.textTertiary,
    flex: 1,
    fontSize: typography.caption.fontSize,
  },
  previewLine: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: 3,
  },
  row: {
    borderRadius: radius.md,
    minHeight: 58,
    paddingHorizontal: spacing.sm + 2,
    // 오른쪽 삭제 버튼이 겹쳐 있는 만큼 비워 둔다.
    paddingRight: 36,
    paddingVertical: spacing.sm,
  },
  rowActive: {
    backgroundColor: colors.primarySoft,
  },
  time: {
    color: colors.textTertiary,
    flexShrink: 0,
    fontSize: typography.micro.fontSize,
  },
  title: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  titleActive: {
    color: colors.primaryDeep,
    fontWeight: '700',
  },
  titleLine: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
  },
  wrapper: {
    position: 'relative',
  },
});

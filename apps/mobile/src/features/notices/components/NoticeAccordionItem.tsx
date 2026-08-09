import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn, LinearTransition, useReducedMotion } from 'react-native-reanimated';

import { colors, spacing, typography } from '@/src/theme';
import type { NoticeItem } from '@/src/types/notice';

const EXPAND_DURATION_MS = 180;

type NoticeAccordionItemProps = {
  notice: NoticeItem;
  isExpanded: boolean;
  onPress: () => void;
};

/** 제목 줄 전체가 토글 버튼이고, 펼쳐지면 본문이 바로 아래에 붙는다. */
export function NoticeAccordionItem({ notice, isExpanded, onPress }: NoticeAccordionItemProps) {
  // 시스템에서 모션 줄이기를 켠 사용자에게는 애니메이션 없이 즉시 펼친다.
  const reducedMotion = useReducedMotion();

  return (
    <Animated.View
      layout={reducedMotion ? undefined : LinearTransition.duration(EXPAND_DURATION_MS)}
      style={styles.item}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: isExpanded }}
        onPress={onPress}
        style={({ pressed }) => [styles.header, pressed && styles.headerPressed]}
      >
        <View style={styles.headerText}>
          <Text style={styles.title}>{notice.title}</Text>
          <Text style={styles.date}>{notice.createdAt}</Text>
        </View>
        <Ionicons
          color={colors.iconGray}
          name={isExpanded ? 'chevron-up' : 'chevron-down'}
          size={20}
        />
      </Pressable>

      {isExpanded ? (
        <Animated.Text
          entering={reducedMotion ? undefined : FadeIn.duration(EXPAND_DURATION_MS)}
          style={styles.content}
        >
          {notice.content}
        </Animated.Text>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  content: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 1,
    lineHeight: 25,
    paddingBottom: spacing.lg,
  },
  date: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.lg,
  },
  headerPressed: {
    opacity: 0.6,
  },
  headerText: {
    flex: 1,
    gap: spacing.sm,
  },
  item: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize + 1,
    fontWeight: '700',
  },
});

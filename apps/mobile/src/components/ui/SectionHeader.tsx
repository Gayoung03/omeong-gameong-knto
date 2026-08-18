import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, typography } from '@/src/theme';

type SectionHeaderProps = {
  title: string;
  /** 오른쪽 링크 문구. `onActionPress` 와 함께 넘겨야 표시된다. */
  actionLabel?: string;
  onActionPress?: () => void;
  /** 바깥 여백처럼 화면마다 다른 값은 여기로 넘긴다. */
  style?: StyleProp<ViewStyle>;
};

/** 화면 안 구획 제목. `제목 + 오른쪽 링크` 한 줄. */
export function SectionHeader({ title, actionLabel, onActionPress, style }: SectionHeaderProps) {
  return (
    <View style={[styles.header, style]}>
      <Text style={styles.title}>{title}</Text>
      {actionLabel && onActionPress ? (
        <Pressable
          accessibilityRole="button"
          hitSlop={10}
          onPress={onActionPress}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <Text style={styles.action}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  action: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  pressed: {
    opacity: 0.55,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '700',
  },
});

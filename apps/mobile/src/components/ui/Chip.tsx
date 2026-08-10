import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type ChipTone = 'orange' | 'mint';

type ChipProps = {
  label: string;
  tone?: ChipTone;
  /** 선택 토글용. 선택되지 않은 칩은 회색 외곽선으로 표시된다. */
  selected?: boolean;
  onPress?: () => void;
  /** 값이 있으면 라벨 오른쪽에 삭제(×) 버튼을 렌더한다. */
  onRemove?: () => void;
  removeAccessibilityLabel?: string;
};

const toneStyles = {
  orange: { background: colors.primarySoft, foreground: colors.primary },
  mint: { background: colors.seaSoftLight, foreground: colors.sea },
} as const;

export function Chip({
  label,
  tone = 'orange',
  selected = true,
  onPress,
  onRemove,
  removeAccessibilityLabel,
}: ChipProps) {
  const { background, foreground } = toneStyles[tone];

  const containerStyle = selected
    ? { backgroundColor: background, borderColor: foreground }
    : { backgroundColor: colors.surface, borderColor: colors.border };
  const labelColor = selected ? foreground : colors.textSecondary;

  return (
    <Pressable
      accessibilityRole={onPress ? 'button' : undefined}
      accessibilityState={onPress ? { selected } : undefined}
      disabled={!onPress}
      onPress={onPress}
      style={[styles.chip, containerStyle]}
    >
      <Text style={[styles.label, { color: labelColor }]}>{label}</Text>
      {onRemove ? (
        <Pressable
          accessibilityLabel={removeAccessibilityLabel ?? `${label} 필터 해제`}
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onRemove}
        >
          <Ionicons color={labelColor} name="close" size={14} />
        </Pressable>
      ) : null}
      {selected && onPress && !onRemove ? (
        <Ionicons color={labelColor} name="checkmark-circle" size={14} />
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignItems: 'center',
    borderRadius: radius.xl,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm + spacing.xs,
    paddingVertical: spacing.xs + 2,
  },
  label: {
    fontSize: typography.body.fontSize - 3,
    fontWeight: '600',
  },
});

/** Chip을 감싸는 가로 목록 컨테이너. 칩이 없으면 아무것도 렌더하지 않는다. */
export function ChipRow({ children }: { children: React.ReactNode }) {
  return <View style={rowStyles.row}>{children}</View>;
}

const rowStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
});

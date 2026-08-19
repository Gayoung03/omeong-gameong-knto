import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { categoryColors, colors, radius, shadow, spacing, typography } from '@/src/theme';

type StatTileVariant = 'blue' | 'green' | 'orange' | 'yellow';

type StatTileProps = {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  /** 개수가 없는 타일(예: 여행 준비 가이드)은 값을 넘기지 않는다. */
  value?: number;
  unit?: string;
  variant: StatTileVariant;
  onPress?: () => void;
};

/**
 * 홈 빠른 메뉴와 같은 `categoryColors` 를 쓴다.
 * 같은 성격의 메뉴가 앱 어디에 있든 같은 색을 갖도록 맞춘 것이다.
 */
const variantColors: Record<StatTileVariant, { background: string; icon: string }> = {
  blue: { background: categoryColors.blue.bg, icon: categoryColors.blue.fg },
  green: { background: categoryColors.green.bg, icon: categoryColors.green.fg },
  orange: { background: categoryColors.orange.bg, icon: categoryColors.orange.fg },
  yellow: { background: categoryColors.yellow.bg, icon: categoryColors.yellow.fg },
};

export function StatTile({ icon, label, value, unit = '개', variant, onPress }: StatTileProps) {
  return (
    <Pressable onPress={onPress} style={styles.tile}>
      <View style={[styles.iconCircle, { backgroundColor: variantColors[variant].background }]}>
        <Ionicons color={variantColors[variant].icon} name={icon} size={18} />
      </View>
      <View style={styles.textGroup}>
        {/* 개수가 없어도 글자 크기는 다른 타일의 라벨과 똑같이 맞춘다. */}
        <Text style={styles.label}>{label}</Text>
        {value === undefined ? (
          // 숫자 줄 자리를 그대로 비워 옆 타일의 라벨과 같은 높이에 놓는다.
          <Text accessibilityElementsHidden importantForAccessibility="no" style={styles.value}>
            {' '}
          </Text>
        ) : (
          <Text style={styles.value}>
            {value}
            {unit}
          </Text>
        )}
      </View>
      <Ionicons color={colors.textSecondary} name="chevron-forward" size={16} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  iconCircle: {
    alignItems: 'center',
    borderRadius: 9999,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
  },
  textGroup: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  tile: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: '48%',
    flexDirection: 'row',
    padding: spacing.md,
    ...shadow.sm,
  },
  value: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    marginTop: spacing.xs / 2,
  },
});

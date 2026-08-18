import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';
import { getPetPolicyLabel, type PetPolicy } from '@/src/types/place';

type PetPolicyBadgeProps = {
  petPolicy: PetPolicy;
};

const BADGE_COLORS: Record<PetPolicy, { background: string; text: string }> = {
  indoorAllowed: { background: colors.seaSoft, text: colors.seaDeep },
  notAllowed: { background: colors.basaltSoft, text: colors.textSecondary },
  outdoorOnly: { background: colors.leafSoft, text: colors.leaf },
  partialAllowed: { background: colors.primarySoft, text: colors.primary },
  // 정책 정보가 없는 장소. 회색으로 두어 '동반 불가'와 헷갈리지 않게 한다.
  unknown: { background: colors.neutralGray, text: colors.textSecondary },
};

/** 반려동물 동반 정책 배지. 내 여행과 장소 탐색이 함께 쓴다. */
export function PetPolicyBadge({ petPolicy }: PetPolicyBadgeProps) {
  const badgeColor = BADGE_COLORS[petPolicy];

  return (
    <View style={[styles.badge, { backgroundColor: badgeColor.background }]}>
      <Text style={[styles.label, { color: badgeColor.text }]}>
        {petPolicy === 'unknown' ? '' : '🐾 '}
        {getPetPolicyLabel(petPolicy)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  label: {
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
});

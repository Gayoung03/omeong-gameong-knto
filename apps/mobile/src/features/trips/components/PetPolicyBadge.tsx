import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { PetPolicy } from '../types/trip';
import { getPetPolicyLabel } from '../utils/tripFormat';

type PetPolicyBadgeProps = {
  petPolicy: PetPolicy;
};

const BADGE_COLORS: Record<PetPolicy, { background: string; text: string }> = {
  outdoorOnly: { background: colors.leafSoft, text: colors.leaf },
  indoorAllowed: { background: colors.seaSoft, text: colors.sea },
  partialAllowed: { background: colors.primarySoft, text: colors.primary },
  notAllowed: { background: colors.basaltSoft, text: colors.textSecondary },
};

export function PetPolicyBadge({ petPolicy }: PetPolicyBadgeProps) {
  const badgeColor = BADGE_COLORS[petPolicy];

  return (
    <View style={[styles.badge, { backgroundColor: badgeColor.background }]}>
      <Text style={[styles.label, { color: badgeColor.text }]}>
        🐾 {getPetPolicyLabel(petPolicy)}
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

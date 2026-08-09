import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';
import { INQUIRY_STATUS_LABEL, type InquiryStatus } from '@/src/types/inquiry';

type Props = {
  status: InquiryStatus;
};

const statusColors: Record<InquiryStatus, { background: string; foreground: string }> = {
  pending: { background: colors.orangeBg, foreground: colors.orangeIcon },
  completed: { background: colors.mintBg, foreground: colors.mintIcon },
};

export function InquiryStatusBadge({ status }: Props) {
  const { background, foreground } = statusColors[status];

  return (
    <View style={[styles.badge, { backgroundColor: background }]}>
      <Text style={[styles.label, { color: foreground }]}>{INQUIRY_STATUS_LABEL[status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs + 1,
  },
  label: {
    fontSize: typography.body.fontSize - 4,
    fontWeight: '700',
  },
});

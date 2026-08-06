import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/src/components/ui/Card';
import { formatShortDate } from '@/src/features/travel-logs/utils/dateFormat';
import { colors, spacing, typography } from '@/src/theme';
import type { InquiryItem } from '@/src/types/inquiry';

import { InquiryStatusBadge } from './InquiryStatusBadge';

type Props = {
  inquiry: InquiryItem;
  onPress: () => void;
};

export function InquiryCard({ inquiry, onPress }: Props) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress}>
      <Card padding="md" style={styles.card}>
        <InquiryStatusBadge status={inquiry.status} />
        <View style={styles.body}>
          <Text style={styles.category}>{inquiry.category}</Text>
          <Text numberOfLines={2} style={styles.title}>
            {inquiry.title}
          </Text>
          <Text style={styles.date}>{formatShortDate(inquiry.createdAt)}</Text>
        </View>
        <Ionicons color={colors.textSecondary} name="chevron-forward" size={18} />
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    gap: spacing.xs,
  },
  card: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  category: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  date: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 4,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
  },
});

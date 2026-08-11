import { StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

import { formatShortDate } from '../utils/dateFormat';

type MemoryCardFrontProps = {
  log: TravelLog;
};

/**
 * 팝업 앞면: 완성 이미지(손글씨·장식은 이미지 안에 이미 포함됨) → 나의 한 줄 → 날짜·장소 순.
 */
export function MemoryCardFront({ log }: MemoryCardFrontProps) {
  return (
    <View style={styles.container}>
      <RemoteImage borderRadius={radius.md} style={styles.image} uri={log.generatedImageUrl} />
      <View style={styles.caption}>
        {log.personalMessage ? (
          <Text numberOfLines={2} style={styles.message}>
            {log.personalMessage}
          </Text>
        ) : null}
        <Text style={styles.meta}>
          {formatShortDate(log.recordedDate)} · {log.placeName}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  caption: {
    gap: spacing.xs / 2,
    paddingHorizontal: spacing.sm,
    paddingTop: spacing.sm,
  },
  container: {
    flex: 1,
  },
  image: {
    flex: 1,
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  message: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
});

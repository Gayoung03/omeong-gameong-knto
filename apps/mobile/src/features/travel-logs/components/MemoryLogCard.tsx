import { Pressable, StyleSheet, Text } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

import { formatShortDate } from '../utils/dateFormat';

type MemoryLogCardProps = {
  log: TravelLog;
  /** 대표 카드는 크게, 나머지는 2열 카드로 표시 */
  size: 'large' | 'small';
  onPress: (logId: string) => void;
};

/** 완성 이미지 → 나의 한 줄 → 날짜·장소 순으로 보여준다. 한 줄이 없으면 제목 영역 자체를 숨긴다. */
export function MemoryLogCard({ log, size, onPress }: MemoryLogCardProps) {
  const metaLabel = `${formatShortDate(log.recordedDate)} · ${log.placeName}`;

  return (
    <Pressable
      accessibilityLabel={`${metaLabel} 기록 앞면 보기`}
      accessibilityRole="button"
      onPress={() => onPress(log.logId)}
      style={styles.card}
    >
      <RemoteImage
        borderRadius={radius.md}
        style={size === 'large' ? styles.imageLarge : styles.imageSmall}
        uri={log.generatedImageUrl}
      />
      {log.personalMessage ? (
        <Text numberOfLines={2} style={styles.message}>
          {log.personalMessage}
        </Text>
      ) : null}
      <Text style={styles.meta}>{metaLabel}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.xs,
  },
  imageLarge: {
    aspectRatio: 1.4,
    width: '100%',
  },
  imageSmall: {
    aspectRatio: 1,
    width: '100%',
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  message: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 2,
    fontWeight: '700',
  },
});

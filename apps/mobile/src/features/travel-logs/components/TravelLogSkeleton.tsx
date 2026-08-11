import { StyleSheet, View } from 'react-native';

import { Card } from '@/src/components/ui/Card';
import { colors, radius, spacing } from '@/src/theme';

const SKELETON_CARD_COUNT = 2;

/** 여행 카드와 같은 형태의 로딩 자리표시자. 전체 화면 스피너 대신 사용한다. */
export function TravelLogSkeleton() {
  return (
    <View style={styles.list}>
      {Array.from({ length: SKELETON_CARD_COUNT }).map((_, index) => (
        <Card key={index} padding="sm" style={styles.card}>
          <View style={styles.titleRow}>
            <View style={[styles.block, styles.title]} />
            <View style={[styles.block, styles.pet]} />
          </View>
          <View style={[styles.block, styles.meta]} />
          <View style={styles.collage}>
            <View style={[styles.block, styles.cover]} />
            <View style={styles.side}>
              <View style={[styles.block, styles.sideTile]} />
              <View style={[styles.block, styles.sideTile]} />
              <View style={[styles.block, styles.sideTile]} />
            </View>
          </View>
        </Card>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.sm,
  },
  card: {
    gap: spacing.sm,
  },
  collage: {
    aspectRatio: 1.15,
    flexDirection: 'row',
    gap: spacing.xs,
  },
  cover: {
    borderRadius: radius.md,
    flex: 2,
  },
  list: {
    gap: spacing.md,
  },
  meta: {
    height: 12,
    width: '55%',
  },
  pet: {
    height: 22,
    width: 64,
  },
  side: {
    flex: 1,
    gap: spacing.xs,
  },
  sideTile: {
    borderRadius: radius.md,
    flex: 1,
  },
  title: {
    height: 18,
    width: '45%',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});

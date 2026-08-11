import { useRouter } from 'expo-router';
import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { Card } from '@/src/components/ui/Card';
import { useAllPets } from '@/src/features/profile/hooks/usePets';
import { colors, spacing, typography } from '@/src/theme';
import type { Trip } from '@/src/types/travelLog';

import { formatDateRangeLabel } from '../utils/dateFormat';
import { resolveCompanions, toPetsById } from '../utils/resolveCompanionDisplay';
import { PhotoCollage } from './PhotoCollage';

type TripCardProps = {
  trip: Trip;
};

export function TripCard({ trip }: TripCardProps) {
  const router = useRouter();
  // 지워진 프로필도 이름을 찾을 수 있도록 전체 목록을 쓴다.
  const { data: allPets = [] } = useAllPets();
  const companions = useMemo(
    () => resolveCompanions(trip.companions, toPetsById(allPets)),
    [allPets, trip.companions],
  );
  const periodLabel = formatDateRangeLabel({ start: trip.startDate, end: trip.endDate });

  return (
    <Pressable
      accessibilityLabel={`${trip.title} 여행 기록 열기`}
      accessibilityRole="button"
      onPress={() =>
        router.push({
          pathname: '/travel-logs/[tripId]',
          params: { tripId: trip.tripId },
        })
      }
    >
      <Card padding="sm" style={styles.card}>
        <View style={styles.titleRow}>
          <Text numberOfLines={1} style={styles.title}>
            {trip.title}
          </Text>
          <View style={styles.pets}>
            {companions.map((companion) => (
              <View key={companion.petId} style={styles.pet}>
                <Avatar fallbackIcon="paw" size={22} uri={companion.profileImage} />
                <Text style={styles.petName}>{companion.name}</Text>
              </View>
            ))}
          </View>
        </View>

        <Text style={styles.meta}>
          {periodLabel} · {trip.logCount}개의 순간
        </Text>

        <PhotoCollage logs={trip.previewLogs} />
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.sm,
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  pet: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  petName: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  pets: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    flexShrink: 1,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
});

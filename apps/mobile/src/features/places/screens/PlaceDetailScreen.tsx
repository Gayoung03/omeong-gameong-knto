import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PetPolicyBadge } from '@/src/components/domain/PetPolicyBadge';
import { EmptyState } from '@/src/components/feedback/EmptyState';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { ReviewPreviewSection } from '@/src/features/reviews/components/ReviewPreviewSection';
import { addRouteItem } from '@/src/features/trips/api/tripsApi';
import { AddScheduleSheet } from '@/src/features/trips/components/AddScheduleSheet';
import { useTrip, tripQueryKeys } from '@/src/features/trips/hooks/useTrips';
import type { AddScheduleInput } from '@/src/features/trips/types/trip';
import { toRouteItemCreateRequest } from '@/src/features/trips/api/routeItemPayload';
import { placeDetailToCandidate } from '@/src/features/trips/api/placeCandidateAdapter';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors, radius, spacing, typography } from '@/src/theme';

import { usePlaceDetail } from '../hooks/usePlaceDetail';
import type { PlaceDetail } from '../types/placeDetail';

type PlaceDetailScreenProps = {
  placeId: string;
  tripId?: string;
  scheduleId?: string;
};

export function PlaceDetailScreen({ placeId, tripId, scheduleId }: PlaceDetailScreenProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: place, isPending } = usePlaceDetail(placeId);
  const tripQuery = useTrip(tripId);
  const [isScheduleSheetOpen, setIsScheduleSheetOpen] = useState(false);
  const [addErrorMessage, setAddErrorMessage] = useState('');

  const addMutation = useMutation({
    mutationFn: (input: AddScheduleInput) => {
      const schedule = tripQuery.data?.schedules.find((item) => item.id === input.scheduleId);
      if (!schedule) throw new Error('여행 날짜를 찾을 수 없어요.');
      return addRouteItem(
        input.scheduleId,
        toRouteItemCreateRequest({
          category: input.place.category,
          date: schedule.date,
          memo: input.memo,
          placeId: input.place.id,
          startTime: input.startTime,
        }),
      );
    },
    onError: (error) => {
      setAddErrorMessage(getApiErrorMessage(error).description);
    },
    onSuccess: async () => {
      if (!tripId) return;
      setIsScheduleSheetOpen(false);
      setAddErrorMessage('');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: tripQueryKeys.detail(tripId) }),
        queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() }),
      ]);
      // 상세 → 장소 탐색을 새 여행 상세로 갈아끼우면 중간 화면이 스택에 남는다.
      // 기존 여행 상세까지 한 번에 닫아, 여기서 뒤로 가면 곧바로 내 여행 목록이 나오게 한다.
      router.dismissTo({ pathname: '/trips/[tripId]', params: { tripId } });
    },
  });

  const isTripPending = Boolean(tripId) && tripQuery.isPending;
  const schedules = tripQuery.data?.schedules ?? [];
  const initialScheduleId =
    schedules.find((schedule) => schedule.id === scheduleId)?.id ?? schedules[0]?.id ?? '';

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title={tripId ? '일정 장소 상세' : '장소 상세'} />

      {isPending || isTripPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : !place ? (
        <EmptyState
          description="주소가 잘못되었거나 삭제된 장소일 수 있어요."
          icon="alert-circle-outline"
          title="장소를 찾을 수 없어요"
        />
      ) : tripId && (tripQuery.isError || !tripQuery.data) ? (
        <EmptyState
          description="내 여행으로 돌아가 다시 장소 추가를 눌러주세요."
          icon="alert-circle-outline"
          title="여행 정보를 불러오지 못했어요"
        />
      ) : (
        <>
          <PlaceDetailView hasRegisterAction={Boolean(tripId)} place={place} />
          {tripId ? (
            <View style={styles.registerFooter}>
              {addErrorMessage ? (
                <Text accessibilityRole="alert" style={styles.registerError}>
                  {addErrorMessage}
                </Text>
              ) : null}
              <Pressable
                accessibilityRole="button"
                disabled={schedules.length === 0 || addMutation.isPending}
                onPress={() => setIsScheduleSheetOpen(true)}
                style={({ pressed }) => [
                  styles.registerButton,
                  (schedules.length === 0 || addMutation.isPending) && styles.disabledButton,
                  pressed && styles.pressed,
                ]}
              >
                <Text style={styles.registerButtonText}>
                  {addMutation.isPending ? '등록하는 중...' : '일정에 등록하기'}
                </Text>
              </Pressable>
            </View>
          ) : null}
          {tripId && isScheduleSheetOpen ? (
            <AddScheduleSheet
              initialScheduleId={initialScheduleId}
              onClose={() => setIsScheduleSheetOpen(false)}
              onSubmit={(input) => {
                setIsScheduleSheetOpen(false);
                addMutation.mutate(input);
              }}
              place={placeDetailToCandidate(place)}
              schedules={schedules}
            />
          ) : null}
        </>
      )}
    </SafeAreaView>
  );
}

function PlaceDetailView({
  hasRegisterAction,
  place,
}: {
  hasRegisterAction: boolean;
  place: PlaceDetail;
}) {
  const chips = [place.region, place.environment].filter((value): value is string =>
    Boolean(value),
  );

  return (
    <ScrollView
      contentContainerStyle={[styles.content, hasRegisterAction && styles.contentWithAction]}
    >
      <RemoteImage borderRadius={radius.lg} style={styles.hero} uri={place.imageUrl ?? undefined} />

      <View style={styles.titleBlock}>
        <View style={styles.titleRow}>
          <Text style={styles.name}>{place.name}</Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{place.categoryLabel}</Text>
          </View>
        </View>

        {(place.rating !== null || place.savedCount !== null) && (
          <View style={styles.statsRow}>
            {place.rating !== null && (
              <View style={styles.stat}>
                <Ionicons color={colors.warning} name="star" size={13} />
                <Text style={styles.statText}>
                  {place.rating.toFixed(1)}
                  {place.reviewCount !== null && ` (${place.reviewCount.toLocaleString()})`}
                </Text>
              </View>
            )}
            {place.savedCount !== null && (
              <View style={styles.stat}>
                <Ionicons color={colors.primary} name="heart" size={13} />
                <Text style={styles.statText}>{place.savedCount.toLocaleString()}</Text>
              </View>
            )}
          </View>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>반려동물 동반</Text>
        <PetPolicyBadge petPolicy={place.petPolicy} />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>주소</Text>
        <View style={styles.addressRow}>
          <Ionicons color={colors.textSecondary} name="location-outline" size={16} />
          <Text style={styles.addressText}>{place.address}</Text>
        </View>

        {chips.length > 0 && (
          <View style={styles.chipRow}>
            {chips.map((chip) => (
              <View key={chip} style={styles.chip}>
                <Text style={styles.chipText}>{chip}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {place.description && (
        <View style={styles.card}>
          <Text style={styles.cardLabel}>소개</Text>
          <Text style={styles.description}>{place.description}</Text>
        </View>
      )}

      {place.isReservable && (
        <View style={styles.notice}>
          <Ionicons color={colors.seaDeep} name="calendar-outline" size={16} />
          <Text style={styles.noticeText}>예약이 가능한 장소예요.</Text>
        </View>
      )}

      <ReviewPreviewSection placeId={place.id} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  addressRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  addressText: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  cardLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: typography.label.fontWeight,
  },
  categoryBadge: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  categoryText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  chip: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  contentWithAction: {
    paddingBottom: spacing.md,
  },
  registerFooter: {
    backgroundColor: colors.surface,
    borderTopColor: colors.divider,
    borderTopWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  registerButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    justifyContent: 'center',
    minHeight: 50,
  },
  registerButtonText: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  registerError: {
    color: colors.error,
    fontSize: typography.caption.fontSize,
    textAlign: 'center',
  },
  disabledButton: {
    opacity: 0.45,
  },
  pressed: {
    opacity: 0.7,
  },
  description: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
  },
  hero: {
    height: 200,
    width: '100%',
  },
  name: {
    color: colors.basalt,
    flexShrink: 1,
    fontSize: typography.title.fontSize,
    fontWeight: '800',
  },
  notice: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm + 4,
  },
  noticeText: {
    color: colors.seaDeep,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  stat: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  statText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  statsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  titleBlock: {
    gap: spacing.sm,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
});

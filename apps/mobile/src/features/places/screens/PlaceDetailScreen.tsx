import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PetPolicyBadge } from '@/src/components/domain/PetPolicyBadge';
import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ErrorState } from '@/src/components/feedback/ErrorState';
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
import type { PlaceIconName } from '../types/place';

type PlaceDetailScreenProps = {
  placeId: string;
  tripId?: string;
  scheduleId?: string;
};

export function PlaceDetailScreen({ placeId, tripId, scheduleId }: PlaceDetailScreenProps) {
  const { data: place, error, isError, isPending, refetch } = usePlaceDetail(placeId);
  const router = useRouter();
  const queryClient = useQueryClient();
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
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
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
  const facilities = getFacilities(place);
  const policyFacts = getPolicyFacts(place);
  const cautionItems = getCautionItems(place);
  const hasOperationInfo = Boolean(
    place.businessHoursRaw || place.closedDaysRaw || place.phone || place.homepageUrl,
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

      {place.description && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>장소 소개</Text>
          <Text style={styles.description}>{place.description}</Text>
        </View>
      )}

      {facilities.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>시설 안내</Text>
          <View style={styles.facilityGrid}>
            {facilities.map((facility) => (
              <View key={facility.label} style={styles.facilityItem}>
                <View style={styles.facilityIcon}>
                  <Ionicons color={colors.primaryDeep} name={facility.icon} size={23} />
                </View>
                <Text style={styles.facilityLabel}>{facility.label}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>반려동물 안내</Text>
        <View style={styles.guideCard}>
          <View style={styles.guideHeading}>
            <Text style={styles.guideTitle}>반려동물 동반 정책</Text>
            <PetPolicyBadge petPolicy={place.petPolicy} />
          </View>
          {policyFacts.length > 0 && (
            <View style={styles.policyFactGrid}>
              {policyFacts.map((fact) => (
                <View key={fact.label} style={styles.policyFact}>
                  <Ionicons color={colors.primaryDeep} name={fact.icon} size={17} />
                  <Text style={styles.policyFactText}>{fact.label}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {place.petPolicyInfo.notes && (
          <View style={styles.guideCard}>
            <View style={styles.guideTitleRow}>
              <Ionicons color={colors.primary} name="information-circle-outline" size={19} />
              <Text style={styles.guideTitle}>추가 안내</Text>
            </View>
            <View style={styles.guideList}>
              {place.petPolicyInfo.notes.split('\n').map((note) => (
                <View key={note} style={styles.guideListRow}>
                  <Ionicons color={colors.primary} name="checkmark-circle-outline" size={17} />
                  <Text style={styles.guideListText}>{note}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {cautionItems.length > 0 && (
          <View style={styles.cautionCard}>
            <Ionicons color={colors.warning} name="warning-outline" size={20} />
            <View style={styles.cautionContent}>
              <Text style={styles.guideTitle}>주의사항</Text>
              <View style={styles.guideList}>
                {cautionItems.map((item) => (
                  <View key={item} style={styles.guideListRow}>
                    <Ionicons color={colors.warning} name="ellipse" size={7} />
                    <Text style={styles.guideListText}>{item}</Text>
                  </View>
                ))}
              </View>
            </View>
          </View>
        )}
      </View>

      {hasOperationInfo && (
        <View style={styles.card}>
          <Text style={styles.cardLabel}>이용 정보</Text>
          {place.businessHoursRaw && (
            <InfoRow icon="time-outline" label="운영시간" value={place.businessHoursRaw} />
          )}
          {place.closedDaysRaw && (
            <InfoRow icon="calendar-outline" label="휴무일" value={place.closedDaysRaw} />
          )}
          {place.phone && <InfoRow icon="call-outline" label="전화" value={place.phone} />}
          {place.homepageUrl && (
            <InfoRow icon="globe-outline" label="홈페이지" value={place.homepageUrl} />
          )}
        </View>
      )}

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

function InfoRow({ icon, label, value }: { icon: PlaceIconName; label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Ionicons color={colors.textSecondary} name={icon} size={17} />
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function getFacilities(place: PlaceDetail): { icon: PlaceIconName; label: string }[] {
  const result: { icon: PlaceIconName; label: string }[] = [];
  const add = (label: string, icon: PlaceIconName) => {
    if (!result.some((item) => item.label === label)) result.push({ icon, label });
  };

  for (const amenity of place.amenities) {
    const compact = amenity.replace(/\s/g, '');
    if (compact.includes('주차')) add('주차 가능', 'car-outline');
    else if (compact.includes('야외') || compact.includes('정원')) add(amenity, 'leaf-outline');
    else if (compact.includes('단체')) add(amenity, 'people-outline');
    else if (compact.includes('대여')) add(amenity, 'bag-handle-outline');
    else add(amenity, 'checkmark-circle-outline');
  }

  return result;
}

function getCautionItems(place: PlaceDetail): string[] {
  const result: string[] = [];
  const add = (item: string) => {
    if (!result.includes(item)) result.push(item);
  };

  for (const item of place.petPolicyInfo.requiredItems.flatMap((value) => value.split(','))) {
    const trimmed = item.trim();
    const compact = trimmed.replace(/\s/g, '');
    if (!trimmed) continue;
    let recognized = false;
    if (compact.includes('배변')) {
      add('배변봉투를 준비해 주세요.');
      recognized = true;
    }
    if (compact.includes('목줄') || compact.includes('리드줄')) {
      add('목줄을 착용해 주세요.');
      recognized = true;
    }
    if (
      compact.includes('케이지') ||
      compact.includes('이동장') ||
      compact.includes('켄넬')
    ) {
      add('이동장이나 케이지를 사용해 주세요.');
      recognized = true;
    }
    if (compact.includes('입마개')) {
      add('입마개를 착용해 주세요.');
      recognized = true;
    }
    if (!recognized) add(trimmed);
  }

  if (place.petPolicyInfo.leashRequired) add('목줄을 착용해 주세요.');
  if (place.petPolicyInfo.carrierRequired) {
    add('이동장이나 케이지를 사용해 주세요.');
  }
  if (place.petPolicyInfo.muzzleRequired) add('입마개를 착용해 주세요.');
  if (place.petPolicyInfo.vaccinationRequired) {
    add('예방접종 증빙을 준비해 주세요.');
  }
  if (place.petPolicyInfo.cautionNote) add(place.petPolicyInfo.cautionNote);
  return result;
}

function getPolicyFacts(place: PlaceDetail): { icon: PlaceIconName; label: string }[] {
  const { allowedSizes, extraFeeAmount, foodAreaAllowed, maxPetsPerPerson, maxWeightKg } =
    place.petPolicyInfo;
  const facts: { icon: PlaceIconName; label: string }[] = [];
  const sizeLabels: Record<string, string> = {
    large: '대형견',
    medium: '중형견',
    small: '소형견',
  };

  if (allowedSizes.length >= 3) {
    facts.push({ icon: 'paw-outline', label: '모든 크기 가능' });
  } else if (allowedSizes.length > 0) {
    facts.push({
      icon: 'paw-outline',
      label: `${allowedSizes.map((size) => sizeLabels[size] ?? size).join(' · ')} 가능`,
    });
  }
  if (maxWeightKg !== null) {
    facts.push({ icon: 'scale-outline', label: `${maxWeightKg}kg 이하` });
  }
  if (maxPetsPerPerson !== null) {
    facts.push({ icon: 'people-outline', label: `1인 ${maxPetsPerPerson}마리까지` });
  }
  if (foodAreaAllowed !== null) {
    facts.push({
      icon: 'restaurant-outline',
      label: `식음료 공간 ${foodAreaAllowed ? '동반 가능' : '동반 불가'}`,
    });
  }
  if (extraFeeAmount !== null) {
    facts.push({
      icon: 'wallet-outline',
      label: extraFeeAmount === 0 ? '추가 요금 없음' : `추가 요금 ${extraFeeAmount.toLocaleString()}원`,
    });
  }
  return facts;
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
  cautionCard: {
    alignItems: 'flex-start',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.lg,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  cautionContent: {
    flex: 1,
    gap: spacing.xs,
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
  facilityGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.lg,
  },
  facilityIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 54,
    justifyContent: 'center',
    width: 54,
  },
  facilityItem: {
    alignItems: 'center',
    gap: spacing.xs,
    minWidth: 92,
  },
  facilityLabel: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    textAlign: 'center',
  },
  guideCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  guideHeading: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
  guideList: {
    gap: spacing.sm,
  },
  guideListRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  guideListText: {
    color: colors.textSecondary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
  },
  guideText: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
  },
  guideTitle: {
    color: colors.textStrong,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
  },
  guideTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  hero: {
    height: 200,
    width: '100%',
  },
  infoLabel: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    width: 58,
  },
  infoRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  infoValue: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.caption.fontSize,
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
  policyFact: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  policyFactGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  policyFactText: {
    color: colors.primaryInk,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  section: {
    gap: spacing.md,
  },
  sectionTitle: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '700',
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

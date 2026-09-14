import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { getApiErrorMessage } from '@/src/services/apiError';
import { colors, spacing, typography } from '@/src/theme';

import { toRouteItemCreateRequest } from '../api/routeItemPayload';
import { addRouteItem } from '../api/tripsApi';
import { usePlaceCandidates } from '../hooks/usePlaceSearch';
import { tripQueryKeys } from '../hooks/useTrips';
import type { PlaceCandidate, Schedule } from '../types/trip';
import { toDaySearchArea } from '../utils/placeSearchArea';

import { PlaceCandidateCard } from './PlaceCandidateCard';

/** 한 날짜에 제안할 최대 장소 수. 너무 많으면 스크롤이 길어진다. */
const MAX_SUGGESTIONS = 4;

type NearbyPlacesSectionProps = {
  tripId: string;
  schedule: Schedule;
  onPressPlace: (placeId: string) => void;
};

/**
 * 그날 **마지막 일정 근처**의 "함께 둘러보면 좋을 장소"를 제안하고 원클릭으로 담는다.
 *
 * 근처 조회·검색 범위 계산·후보 카드·추가 요청은 이미 있는 것을 그대로 쓴다
 * (`usePlaceCandidates('dayRecommend')` + `toDaySearchArea` + `PlaceCandidateCard` + `addRouteItem`).
 * 여기서 새로 하는 일은 여행 상세에 이 목록을 붙이고, 이미 담긴 장소를 빼고,
 * 담기 결과를 상세·목록 캐시에 반영하는 것뿐이다.
 */
export function NearbyPlacesSection({ tripId, schedule, onPressPlace }: NearbyPlacesSectionProps) {
  const queryClient = useQueryClient();
  const [addedIds, setAddedIds] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState('');

  const area = useMemo(() => toDaySearchArea(schedule.items), [schedule.items]);
  const { data: candidates, isLoading } = usePlaceCandidates('dayRecommend', null, area);

  // 이미 담긴 장소는 제안에서 뺀다. 공식 장소는 place.id 가 서버 place id 라 그대로 비교된다
  // (커스텀 일정의 id 는 route-item id 라 후보와 겹치지 않는다).
  const existingIds = useMemo(
    () => new Set(schedule.items.map((item) => item.place.id)),
    [schedule.items],
  );

  const suggestions = useMemo(() => {
    if (!candidates) {
      return [];
    }
    return candidates.filter((place) => !existingIds.has(place.id)).slice(0, MAX_SUGGESTIONS);
  }, [candidates, existingIds]);

  const addMutation = useMutation({
    mutationFn: (place: PlaceCandidate) =>
      addRouteItem(
        schedule.id,
        toRouteItemCreateRequest({
          category: place.category,
          date: schedule.date,
          memo: '',
          placeId: place.id,
          startTime: null,
        }),
      ),
    // 누르는 즉시 '담김'으로 바꾼다(낙관적). 실패하면 되돌린다.
    onMutate: (place) => {
      setErrorMessage('');
      setAddedIds((prev) => [...prev, place.id]);
    },
    onError: (error, place) => {
      setAddedIds((prev) => prev.filter((id) => id !== place.id));
      setErrorMessage(getApiErrorMessage(error).description);
    },
    // 서버가 sortOrder·이동시간을 다시 매기므로 캐시를 직접 만지지 않고 다시 받아온다.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: tripQueryKeys.detail(tripId) }),
        queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() }),
      ]),
  });

  // 그날 일정이 하나도 없으면 기준점이 없다(부모도 이 경우 렌더하지 않는다).
  if (!area) {
    return null;
  }

  // 조회가 끝났는데 제안할 게 없으면 섹션을 통째로 숨긴다.
  if (!isLoading && suggestions.length === 0) {
    return null;
  }

  return (
    <View style={styles.section}>
      <Text style={styles.title}>함께 둘러보면 좋을 장소</Text>
      <Text style={styles.subtitle}>Day {schedule.dayNumber} 마지막 일정 근처예요</Text>

      {errorMessage ? <Text style={styles.error}>{errorMessage}</Text> : null}

      {isLoading ? (
        <ActivityIndicator color={colors.primary} style={styles.loading} />
      ) : (
        suggestions.map((place) => (
          <PlaceCandidateCard
            key={place.id}
            isAdded={addedIds.includes(place.id)}
            isSelected={false}
            onPress={onPressPlace}
            onPressSelect={(selected) => addMutation.mutate(selected)}
            place={place}
          />
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    paddingTop: spacing.lg,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize - 2,
    fontWeight: '700',
    paddingHorizontal: spacing.lg - 4,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    paddingBottom: spacing.xs,
    paddingHorizontal: spacing.lg - 4,
    paddingTop: 2,
  },
  error: {
    color: colors.error,
    fontSize: typography.caption.fontSize,
    paddingHorizontal: spacing.lg - 4,
    paddingVertical: spacing.xs,
  },
  loading: {
    paddingVertical: spacing.lg,
  },
});

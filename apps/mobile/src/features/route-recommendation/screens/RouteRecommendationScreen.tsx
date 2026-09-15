import Ionicons from '@expo/vector-icons/Ionicons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import {
  Image,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { clearPendingRoute, loadPendingRoute, savePendingRoute } from '../services/pendingRoute';
import { searchAccommodations, searchPlaces } from '@/src/features/places/api/placesApi';
import type { Place } from '@/src/features/places/types/place';
import { toAnimalHospital } from '@/src/features/trips/api/routeAdapter';
import { AnimalHospitalSection } from '@/src/features/trips/components/AnimalHospitalSection';
import {
  addRouteItem,
  createRouteRecommendation,
  getRouteGenerationStatus,
  getTripRaw,
  replaceRouteItemPlace,
  requestRouteEditSuggestions,
  updateRouteItem,
  updateTrip,
} from '@/src/features/trips/api/tripsApi';
import type {
  RouteEditSuggestionResponse,
  RouteItemCandidateResponse,
  RouteItemResponse,
  RouteRequestCreateRequest,
  ServerScheduleItemType,
} from '@/src/features/trips/types/routeApi';
import { colors, overlayColors } from '@/src/theme';

const POLL_MS = 2_000;
const TIMEOUT_MS = 3 * 60 * 1_000;

function errorMessage(error: unknown): string {
  if (isAxiosError<{ detail?: string }>(error)) {
    if (error.response?.data?.detail) return error.response.data.detail;
    if (error.response?.status === 504)
      return '요청 처리가 늦어지고 있어요. 잠시 후 다시 시도해주세요.';
    if (error.response?.status === 502)
      return '수정 요청을 이해하지 못했어요. 더 구체적으로 적어주세요.';
  }
  return '네트워크 연결을 확인하고 다시 시도해주세요.';
}

const formatTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(new Date(value))
    : '시간 미정';

/** 이전에 저장된 추천 결과의 내부 데이터 출처 표기도 사용자 문구로 정리한다. */
function publicRecommendationCopy(value: string): string {
  return value
    .replace(/한국관광공사\s*TourAPI\s*실시간 정보 확인/gi, '최신 관광정보 확인')
    .replace(/한국관광공사\s*TourAPI\s*실시간 관광정보/gi, '최신 주변 관광정보')
    .replace(/한국관광공사\s*TourAPI\s*실시간 조회/gi, '최신 주변 정보 조회')
    .replace(/한국관광공사\s*TourAPI\s*/gi, '')
    .replace(/TourAPI\s*/gi, '')
    .replace(/DB 장소/g, '등록된 장소')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

const ITEM_TYPES = new Set<ServerScheduleItemType>([
  'accommodation',
  'attraction',
  'cafe',
  'restaurant',
]);

function serverItemType(place: Place): ServerScheduleItemType {
  const category = place.serverCategory;
  if (category === 'restaurant_cafe') return 'restaurant';
  if (['beach', 'oreum', 'rental_experience', 'walking_trail'].includes(category ?? '')) {
    return 'attraction';
  }
  return category && ITEM_TYPES.has(category as ServerScheduleItemType)
    ? (category as ServerScheduleItemType)
    : 'custom';
}

function timePart(value: string | null): string {
  return value?.slice(11, 16) ?? '';
}

/** 빈 슬롯 카드 제목에 쓰는 자리 이름. 서버는 못 채운 슬롯의 `itemType` 만 남긴다. */
const SLOT_LABELS: Record<ServerScheduleItemType, string> = {
  restaurant: '식당',
  cafe: '카페',
  attraction: '관광지',
  accommodation: '숙소',
  custom: '장소',
};

function callPhone(phone: string) {
  void Linking.openURL(`tel:${phone.replace(/[^0-9+]/g, '')}`);
}

function CandidateRow({
  candidate,
  onPick,
}: {
  candidate: RouteItemCandidateResponse;
  onPick: () => void;
}) {
  const phone = candidate.phone;
  return (
    <View style={styles.candidateRow}>
      <View style={styles.itemCopy}>
        <View style={styles.candidateTitleRow}>
          <Text numberOfLines={1} style={styles.candidateName}>
            {candidate.name}
          </Text>
          {candidate.requiresVerification ? (
            <Text style={styles.verifyChip}>확인 필요</Text>
          ) : null}
        </View>
        <Text numberOfLines={2} style={styles.itemReason}>
          {candidate.recommendationReason
            ? publicRecommendationCopy(candidate.recommendationReason)
            : (candidate.address ?? '')}
        </Text>
      </View>
      {phone ? (
        <Pressable
          accessibilityLabel={`${candidate.name} 전화`}
          hitSlop={8}
          onPress={() => callPhone(phone)}
        >
          <Ionicons color={colors.textSecondary} name="call-outline" size={19} />
        </Pressable>
      ) : null}
      <Pressable accessibilityLabel={`${candidate.name} 담기`} hitSlop={8} onPress={onPick}>
        <Text style={styles.replaceText}>담기</Text>
      </Pressable>
    </View>
  );
}

function RouteItemCard({
  item,
  onOpen,
  onPickCandidate,
  onReplace,
  onTime,
  onToggle,
}: {
  item: RouteItemResponse;
  onOpen: () => void;
  onPickCandidate: (candidate: RouteItemCandidateResponse) => void;
  onReplace: () => void;
  onTime: () => void;
  onToggle: () => void;
}) {
  const isUnfilled = item.slotStatus === 'unfilled';
  const needsVerification = item.slotStatus === 'needs_verification';
  const slotLabel = SLOT_LABELS[item.itemType];
  const name = item.place?.name ?? item.customPlaceName ?? (isUnfilled ? `${slotLabel} 자리` : '일정');
  // 빈 슬롯도 교체 API 로 채운다 (PUT /route-items/{id}/place).
  const canReplace = (Boolean(item.place) || isUnfilled) && item.itemType !== 'custom';
  const phone = item.place?.phone ?? null;
  return (
    <>
      <View style={[styles.itemCard, isUnfilled && styles.itemCardUnfilled]}>
        <Pressable
          accessibilityHint={item.place ? '장소 상세 정보를 확인할 수 있어요' : undefined}
          accessibilityRole={item.place ? 'button' : undefined}
          disabled={!item.place}
          onPress={onOpen}
          style={({ pressed }) => [styles.itemMain, pressed && styles.itemMainPressed]}
        >
          {item.place?.primaryImageUrl ? (
            <Image source={{ uri: item.place.primaryImageUrl }} style={styles.thumbnail} />
          ) : (
            <View style={[styles.thumbnail, styles.thumbnailPlaceholder]}>
              <Ionicons
                color={colors.textTertiary}
                name={isUnfilled ? 'help-circle-outline' : 'image-outline'}
                size={24}
              />
            </View>
          )}
          <View style={styles.itemCopy}>
            <Text style={styles.itemTime}>{formatTime(item.startsAt)}</Text>
            <View style={styles.candidateTitleRow}>
              <Text numberOfLines={1} style={[styles.itemName, isUnfilled && styles.itemNameMuted]}>
                {isUnfilled ? `${slotLabel} 자리가 비어 있어요` : name}
              </Text>
              {needsVerification ? <Text style={styles.verifyChip}>확인 필요</Text> : null}
            </View>
            <Text numberOfLines={2} style={styles.itemReason}>
              {isUnfilled
                ? '조건에 맞는 곳을 찾지 못했어요. 아래 후보에서 고르거나 직접 찾아보세요.'
                : item.recommendationReason
                  ? publicRecommendationCopy(item.recommendationReason)
                  : (item.place?.address ?? '상세 정보를 확인해주세요.')}
            </Text>
            {item.recommendationScore !== null ? (
              <Text style={styles.scoreText}>추천 점수 {Math.round(item.recommendationScore)}점</Text>
            ) : null}
          </View>
        </Pressable>
        {item.recommendationScore !== null || canReplace || item.startsAt !== null || phone ? (
          <View style={styles.itemActions}>
            {item.recommendationScore !== null ? (
              <Pressable accessibilityLabel={`${name} 선택`} onPress={onToggle}>
                <Ionicons
                  color={item.isSelected ? colors.seaDeep : colors.textTertiary}
                  name={item.isSelected ? 'checkmark-circle' : 'ellipse-outline'}
                  size={23}
                />
              </Pressable>
            ) : null}
            {needsVerification && phone ? (
              <Pressable accessibilityLabel={`${name} 전화로 확인`} onPress={() => callPhone(phone)}>
                <Ionicons color={colors.textSecondary} name="call-outline" size={21} />
              </Pressable>
            ) : null}
            {canReplace ? (
              <Pressable
                accessibilityLabel={isUnfilled ? `${name} 채우기` : `${name} 장소 변경`}
                onPress={onReplace}
              >
                <Ionicons color={colors.primary} name="swap-horizontal" size={22} />
              </Pressable>
            ) : null}
            <Pressable accessibilityLabel={`${name} 시간 변경`} onPress={onTime}>
              <Ionicons color={colors.textSecondary} name="time-outline" size={21} />
            </Pressable>
          </View>
        ) : null}
      </View>
      {item.candidates.length ? (
        <View style={styles.candidateBox}>
          <Text style={styles.candidateHeader}>
            {isUnfilled ? '이 자리에 넣을 만한 곳' : '대신 갈 만한 곳'}
          </Text>
          {item.candidates.map((candidate) => (
            <CandidateRow
              key={candidate.placeId}
              candidate={candidate}
              onPick={() => onPickCandidate(candidate)}
            />
          ))}
        </View>
      ) : null}
    </>
  );
}

export function RouteRecommendationScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { routeId, petName } = useLocalSearchParams<{ routeId?: string; petName?: string }>();
  const [startedAt, setStartedAt] = useState(0);
  const [timedOut, setTimedOut] = useState(false);
  const [pendingRequest, setPendingRequest] = useState<RouteRequestCreateRequest | null>(null);
  const [feedback, setFeedback] = useState('');
  const [selectedDay, setSelectedDay] = useState(0);
  const [editingItem, setEditingItem] = useState<RouteItemResponse | null>(null);
  const [addingPlace, setAddingPlace] = useState(false);
  const [editMode, setEditMode] = useState<'choose' | 'ai' | 'search' | 'time'>('choose');
  const [timeValue, setTimeValue] = useState('');
  const [instruction, setInstruction] = useState('');
  const [suggestions, setSuggestions] = useState<RouteEditSuggestionResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Place[]>([]);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    void loadPendingRoute().then((pending) => {
      if (pending && pending.routeId === routeId) {
        setStartedAt(pending.startedAt);
        setPendingRequest(pending.request ?? null);
      } else {
        setStartedAt(Date.now());
      }
    });
  }, [routeId]);

  const statusQuery = useQuery({
    queryKey: ['route-generation-status', routeId],
    queryFn: () => getRouteGenerationStatus(routeId!),
    enabled: Boolean(routeId) && startedAt > 0 && !timedOut,
    retry: 2,
    refetchInterval: (query) => {
      const current = query.state.data?.status;
      if (current === 'generated' || current === 'failed') return false;
      return POLL_MS;
    },
  });
  const status = statusQuery.data?.status;
  useEffect(() => {
    if (status === 'generated') void clearPendingRoute();
  }, [status]);
  useEffect(() => {
    if (!startedAt || status === 'generated' || status === 'failed') return;
    const remaining = Math.max(0, TIMEOUT_MS - (Date.now() - startedAt));
    const timer = setTimeout(() => setTimedOut(true), remaining);
    return () => clearTimeout(timer);
  }, [startedAt, status]);

  const routeQuery = useQuery({
    queryKey: ['route-recommendation', routeId],
    queryFn: () => getTripRaw(routeId!),
    enabled: Boolean(routeId) && status === 'generated',
  });
  const route = routeQuery.data;
  const activeDay = route?.routeDays[selectedDay];
  const selectedCount = useMemo(
    () =>
      route?.routeDays
        .flatMap((day) => day.items)
        .filter((item) => item.recommendationScore !== null && item.isSelected).length ?? 0,
    [route],
  );
  const refreshRoute = () =>
    queryClient.invalidateQueries({ queryKey: ['route-recommendation', routeId] });

  const toggleItem = async (item: RouteItemResponse) => {
    try {
      await updateRouteItem(item.id, { isSelected: !item.isSelected });
      await refreshRoute();
    } catch (error) {
      setFeedback(errorMessage(error));
    }
  };
  const saveRoute = async () => {
    if (!routeId) return;
    try {
      await updateTrip(routeId, { status: 'saved' });
      setFeedback('코스를 저장했어요. 내 여행에서 다시 확인할 수 있어요.');
    } catch (error) {
      setFeedback(errorMessage(error));
    }
  };
  const shareRoute = async () => {
    if (!route) return;
    const text = route.routeDays
      .map(
        (day) =>
          `${day.dayNumber}일차\n${day.items.map((item) => `${formatTime(item.startsAt)} ${item.place?.name ?? item.customPlaceName ?? `(${SLOT_LABELS[item.itemType]} 자리 비어 있음)`}`).join('\n')}`,
      )
      .join('\n\n');
    await Share.share({ title: route.title, message: `${route.title}\n\n${text}` });
  };
  const openEditor = (item: RouteItemResponse, mode: 'choose' | 'time' = 'choose') => {
    setEditingItem(item);
    setEditMode(mode);
    setTimeValue(timePart(item.startsAt));
  };
  const openAddPlace = () => {
    const lastVisit = [...(activeDay?.items ?? [])]
      .reverse()
      .find((item) => item.itemType !== 'accommodation');
    setAddingPlace(true);
    setEditMode('search');
    setTimeValue(timePart(lastVisit?.endsAt ?? null));
  };
  const closeEditor = () => {
    setEditingItem(null);
    setAddingPlace(false);
    setEditMode('choose');
    setTimeValue('');
    setInstruction('');
    setSuggestions(null);
    setSearchQuery('');
    setSearchResults([]);
    setActionError('');
  };
  const askAi = async () => {
    if (!routeId || !editingItem || !instruction.trim()) return;
    setActionLoading(true);
    setActionError('');
    try {
      const result = await requestRouteEditSuggestions(routeId, editingItem.id, instruction.trim());
      setSuggestions(result);
      if (!result.suggestions.length) setActionError('조건에 맞는 대체 장소를 찾지 못했어요.');
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setActionLoading(false);
    }
  };
  const search = async () => {
    if (!searchQuery.trim()) return;
    setActionLoading(true);
    setActionError('');
    try {
      setSearchResults(
        await (editingItem?.itemType === 'accommodation'
          ? searchAccommodations(searchQuery.trim())
          : searchPlaces(searchQuery.trim())),
      );
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setActionLoading(false);
    }
  };
  const replacePlace = async (
    placeId: string,
    targetItemId = editingItem?.id,
    message = '일정의 장소를 변경했어요.',
  ) => {
    if (!targetItemId) return;
    setActionLoading(true);
    setActionError('');
    try {
      await replaceRouteItemPlace(targetItemId, placeId);
      await refreshRoute();
      closeEditor();
      setFeedback(message);
    } catch (error) {
      // 카드의 후보 담기는 시트 밖이라 시트 오류 대신 화면 피드백으로 보여준다.
      if (editingItem || addingPlace) setActionError(errorMessage(error));
      else setFeedback(errorMessage(error));
    } finally {
      setActionLoading(false);
    }
  };
  const pickCandidate = (item: RouteItemResponse, candidate: RouteItemCandidateResponse) =>
    replacePlace(
      candidate.placeId,
      item.id,
      item.slotStatus === 'unfilled'
        ? `${candidate.name}(으)로 빈 일정을 채웠어요.`
        : `${candidate.name}(으)로 바꿨어요.`,
    );
  const saveTime = async () => {
    if (!editingItem || !activeDay || !/^([01]\d|2[0-3]):[0-5]\d$/.test(timeValue)) {
      setActionError('시간을 HH:MM 형식으로 입력해주세요.');
      return;
    }
    setActionLoading(true);
    setActionError('');
    try {
      const startsAt = `${activeDay.routeDate}T${timeValue}:00+09:00`;
      const duration =
        editingItem.startsAt && editingItem.endsAt
          ? Math.max(
              0,
              (new Date(editingItem.endsAt).getTime() - new Date(editingItem.startsAt).getTime()) /
                60_000,
            )
          : (editingItem.stayMinutes ?? 0);
      await updateRouteItem(editingItem.id, {
        startsAt,
        ...(duration > 0
          ? { endsAt: new Date(new Date(startsAt).getTime() + duration * 60_000).toISOString() }
          : {}),
      });
      await refreshRoute();
      closeEditor();
      setFeedback('일정 시간을 변경했어요.');
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setActionLoading(false);
    }
  };
  const addPlace = async (place: Place) => {
    if (!activeDay || !/^([01]\d|2[0-3]):[0-5]\d$/.test(timeValue)) {
      setActionError('추가할 시간을 HH:MM 형식으로 입력해주세요.');
      return;
    }
    const last = activeDay.items.at(-1);
    const position = last?.itemType === 'accommodation' ? last.sortOrder : activeDay.items.length;
    setActionLoading(true);
    setActionError('');
    try {
      await addRouteItem(activeDay.id, {
        itemType: serverItemType(place),
        placeId: place.id,
        sortOrder: position,
        startsAt: `${activeDay.routeDate}T${timeValue}:00+09:00`,
      });
      await refreshRoute();
      closeEditor();
      setFeedback(`${place.name}을(를) 일정에 추가했어요.`);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setActionLoading(false);
    }
  };

  const retryGeneration = async () => {
    if (!pendingRequest) {
      router.replace('/routes');
      return;
    }
    try {
      const accepted = await createRouteRecommendation(pendingRequest);
      await savePendingRoute({
        routeId: accepted.routeId,
        startedAt: Date.now(),
        request: pendingRequest,
      });
      router.replace({
        pathname: '/routes/result',
        params: { routeId: accepted.routeId, petName },
      });
    } catch (error) {
      setFeedback(errorMessage(error));
    }
  };

  if (!routeId)
    return (
      <StateScreen
        title="추천 정보가 없어요"
        description="입력 화면에서 다시 추천을 요청해주세요."
        onPress={() => router.replace('/routes')}
        button="다시 입력"
      />
    );
  if (status === 'failed')
    return (
      <StateScreen
        title="루트를 만들지 못했어요"
        description={
          feedback || statusQuery.data?.failureReason || '조건을 확인하고 다시 요청해주세요.'
        }
        onPress={() => void retryGeneration()}
        button={pendingRequest ? '다시 추천받기' : '조건 다시 입력'}
      />
    );
  if (timedOut)
    return (
      <StateScreen
        title="추천에 시간이 더 필요해요"
        description="서버에서는 계속 만들고 있어요."
        onPress={() => {
          setStartedAt(Date.now());
          setTimedOut(false);
        }}
        button="다시 확인"
      />
    );
  if (statusQuery.isError)
    return (
      <StateScreen
        title="상태를 확인하지 못했어요"
        description={errorMessage(statusQuery.error)}
        onPress={() => void statusQuery.refetch()}
        button="다시 시도"
      />
    );
  if (status !== 'generated' || routeQuery.isPending)
    return (
      <StateScreen
        title="맞춤 루트를 만드는 중이에요"
        description="반려동물 조건과 선호, 이동 부담을 함께 살펴보고 있어요."
      />
    );
  if (routeQuery.isError || !route || !activeDay)
    return (
      <StateScreen
        title="추천 결과를 불러오지 못했어요"
        description={errorMessage(routeQuery.error)}
        onPress={() => void routeQuery.refetch()}
        button="다시 시도"
      />
    );

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable accessibilityLabel="돌아가기" onPress={() => router.back()}>
          <Ionicons color={colors.textPrimary} name="chevron-back" size={25} />
        </Pressable>
        <View style={styles.headerCopy}>
          <Text style={styles.eyebrow}>맞춤 여행 플래너</Text>
          <Text style={styles.headerTitle}>추천 결과</Text>
        </View>
        <Pressable accessibilityLabel="공유" onPress={() => void shareRoute()}>
          <Ionicons color={colors.textPrimary} name="share-outline" size={23} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}>
          <Text style={styles.heroBadge}>🐾 혼디 추천 코스</Text>
          <Text style={styles.heroTitle}>
            {petName ? `${petName}와 함께하는 ` : ''}
            {route.title}
          </Text>
          {route.explanation ? (
            <Text style={styles.heroDescription}>
              {publicRecommendationCopy(route.explanation)}
            </Text>
          ) : null}
          {route.tourApiPlaces.length > 0 ? (
            <View style={styles.tourApiBadge}>
              <Ionicons color={colors.seaDeep} name="business-outline" size={14} />
              <Text style={styles.tourApiBadgeText}>최신 추천 정보 반영</Text>
            </View>
          ) : null}
          {route.slotSummary.unfilled + route.slotSummary.needsVerification > 0 ? (
            <View style={styles.slotBadge}>
              <Ionicons color={colors.primaryDeep} name="alert-circle-outline" size={14} />
              <Text style={styles.slotBadgeText}>
                {[
                  route.slotSummary.needsVerification > 0
                    ? `확인 필요 ${route.slotSummary.needsVerification}곳`
                    : null,
                  route.slotSummary.unfilled > 0
                    ? `비어 있는 자리 ${route.slotSummary.unfilled}곳`
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </Text>
            </View>
          ) : null}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dayScroller}>
          {route.routeDays.map((day, index) => (
            <Pressable
              key={day.id}
              onPress={() => setSelectedDay(index)}
              style={[styles.dayTab, index === selectedDay && styles.dayTabActive]}
            >
              <Text style={[styles.dayText, index === selectedDay && styles.dayTextActive]}>
                {day.dayNumber}일차
              </Text>
              <Text style={[styles.dayDate, index === selectedDay && styles.dayTextActive]}>
                {day.routeDate.slice(5)}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
        <Text style={styles.sectionTitle}>
          {activeDay.title ?? `${activeDay.dayNumber}일차 일정`}
        </Text>
        {activeDay.items.length ? (
          activeDay.items.map((item) => (
            <RouteItemCard
              key={item.id}
              item={item}
              onOpen={() =>
                item.place &&
                router.push({
                  pathname: '/places/[placeId]',
                  params: { placeId: item.place.id },
                })
              }
              onPickCandidate={(candidate) => void pickCandidate(item, candidate)}
              onReplace={() => openEditor(item)}
              onTime={() => openEditor(item, 'time')}
              onToggle={() => void toggleItem(item)}
            />
          ))
        ) : (
          <Text style={styles.emptyText}>추천된 일정이 없어요.</Text>
        )}
        <Pressable onPress={openAddPlace} style={styles.addButton}>
          <Ionicons color={colors.seaDeep} name="add-circle-outline" size={20} />
          <Text style={styles.addButtonText}>장소 추가</Text>
        </Pressable>
        <AnimalHospitalSection
          hospitals={route.nearbyAnimalHospitals.map(toAnimalHospital)}
          inset={false}
        />
        {route.tourApiPlaces.length ? (
          <View style={styles.tourApiSection}>
            <Text style={styles.tourApiSectionTitle}>함께 둘러보기 좋은 곳</Text>
            <Text style={styles.tourApiSectionDescription}>
              여행 동선 주변에서 같이 방문하기 좋은 장소를 모았어요.
            </Text>
            {route.tourApiPlaces.map((place) => (
              <View key={place.contentId} style={styles.tourApiCard}>
                {place.imageUrl ? (
                  <Image source={{ uri: place.imageUrl }} style={styles.tourApiImage} />
                ) : (
                  <View style={[styles.tourApiImage, styles.thumbnailPlaceholder]}>
                    <Ionicons color={colors.textTertiary} name="image-outline" size={22} />
                  </View>
                )}
                <View style={styles.itemCopy}>
                  <Text style={styles.itemName}>{place.title}</Text>
                  <Text numberOfLines={2} style={styles.itemReason}>
                    {place.address ?? '주소 정보 없음'}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        ) : null}
        {feedback ? (
          <Text accessibilityRole="alert" style={styles.feedback}>
            {feedback}
          </Text>
        ) : null}
        <Pressable
          disabled={selectedCount === 0}
          onPress={() => void saveRoute()}
          style={[styles.primaryButton, selectedCount === 0 && styles.disabled]}
        >
          <Text style={styles.primaryText}>선택한 코스 저장하기</Text>
        </Pressable>
      </ScrollView>
      <Modal
        animationType="slide"
        transparent
        visible={editingItem !== null || addingPlace}
        onRequestClose={closeEditor}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.sheet}>
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>
                {addingPlace
                  ? '일정에 장소 추가'
                  : editMode === 'time'
                    ? '일정 시간 변경'
                    : editingItem?.slotStatus === 'unfilled'
                      ? '빈 일정 채우기'
                      : '일정 장소 변경'}
              </Text>
              <Pressable onPress={closeEditor}>
                <Ionicons color={colors.textSecondary} name="close" size={24} />
              </Pressable>
            </View>
            {editMode === 'choose' ? (
              <>
                <Pressable onPress={() => setEditMode('ai')} style={styles.methodButton}>
                  <Ionicons color={colors.primary} name="sparkles" size={22} />
                  <View>
                    <Text style={styles.methodTitle}>AI에게 변경 요청</Text>
                    <Text style={styles.methodDescription}>원하는 조건을 말로 알려주세요.</Text>
                  </View>
                </Pressable>
                <Pressable onPress={() => setEditMode('search')} style={styles.methodButton}>
                  <Ionicons color={colors.seaDeep} name="search" size={22} />
                  <View>
                    <Text style={styles.methodTitle}>직접 장소 찾기</Text>
                    <Text style={styles.methodDescription}>장소 이름으로 검색해요.</Text>
                  </View>
                </Pressable>
                <Pressable onPress={() => setEditMode('time')} style={styles.methodButton}>
                  <Ionicons color={colors.textSecondary} name="time-outline" size={22} />
                  <View>
                    <Text style={styles.methodTitle}>시간 변경</Text>
                    <Text style={styles.methodDescription}>이 장소의 시작 시간을 바꿔요.</Text>
                  </View>
                </Pressable>
              </>
            ) : null}
            {editMode === 'ai' ? (
              <>
                <TextInput
                  multiline
                  onChangeText={setInstruction}
                  placeholder="예: 비 오는 날 갈 수 있는 실내 곳으로 바꿔줘"
                  style={styles.textArea}
                  value={instruction}
                />
                <Pressable
                  disabled={actionLoading || !instruction.trim()}
                  onPress={() => void askAi()}
                  style={styles.primaryButton}
                >
                  <Text style={styles.primaryText}>
                    {actionLoading ? '찾는 중...' : '대체 장소 찾기'}
                  </Text>
                </Pressable>
                {suggestions ? (
                  <>
                    <Text style={styles.interpretation}>{suggestions.interpretation}</Text>
                    {suggestions.suggestions.map((place) => (
                      <ResultRow
                        key={place.placeId}
                        name={place.name}
                        detail={place.recommendationReason}
                        onPress={() => void replacePlace(place.placeId)}
                      />
                    ))}
                  </>
                ) : null}
              </>
            ) : null}
            {editMode === 'search' ? (
              <>
                {addingPlace ? (
                  <View style={styles.timeRow}>
                    <Text style={styles.timeLabel}>방문 시간</Text>
                    <TextInput
                      keyboardType="numbers-and-punctuation"
                      maxLength={5}
                      onChangeText={setTimeValue}
                      placeholder="예: 15:30"
                      style={styles.timeInput}
                      value={timeValue}
                    />
                  </View>
                ) : null}
                <View style={styles.searchRow}>
                  <TextInput
                    onChangeText={setSearchQuery}
                    onSubmitEditing={() => void search()}
                    placeholder="장소 이름"
                    style={styles.searchInput}
                    value={searchQuery}
                  />
                  <Pressable onPress={() => void search()} style={styles.searchButton}>
                    <Ionicons color={colors.surface} name="search" size={20} />
                  </Pressable>
                </View>
                {searchResults.map((place) => (
                  <ResultRow
                    key={place.id}
                    name={place.name}
                    detail={place.address}
                    label={addingPlace ? '추가' : '변경'}
                    onPress={() =>
                      addingPlace ? void addPlace(place) : void replacePlace(place.id)
                    }
                  />
                ))}
              </>
            ) : null}
            {editMode === 'time' ? (
              <>
                <Text style={styles.timeHelp}>24시간 형식으로 입력해주세요.</Text>
                <TextInput
                  autoFocus
                  keyboardType="numbers-and-punctuation"
                  maxLength={5}
                  onChangeText={setTimeValue}
                  placeholder="예: 14:30"
                  style={styles.timeInput}
                  value={timeValue}
                />
                <Pressable
                  disabled={actionLoading}
                  onPress={() => void saveTime()}
                  style={styles.primaryButton}
                >
                  <Text style={styles.primaryText}>
                    {actionLoading ? '변경 중...' : '시간 변경하기'}
                  </Text>
                </Pressable>
              </>
            ) : null}
            {actionError ? (
              <Text accessibilityRole="alert" style={styles.error}>
                {actionError}
              </Text>
            ) : null}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function ResultRow({
  name,
  detail,
  label = '변경',
  onPress,
}: {
  name: string;
  detail: string;
  label?: string;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={styles.resultRow}>
      <View style={styles.itemCopy}>
        <Text style={styles.itemName}>{name}</Text>
        <Text numberOfLines={2} style={styles.itemReason}>
          {detail}
        </Text>
      </View>
      <Text style={styles.replaceText}>{label}</Text>
    </Pressable>
  );
}
function StateScreen({
  title,
  description,
  button,
  onPress,
}: {
  title: string;
  description: string;
  button?: string;
  onPress?: () => void;
}) {
  return (
    <SafeAreaView style={styles.state}>
      <Ionicons color={colors.primary} name="paw" size={46} />
      <Text style={styles.stateTitle}>{title}</Text>
      <Text style={styles.stateDescription}>{description}</Text>
      {button && onPress ? (
        <Pressable onPress={onPress} style={styles.stateButton}>
          <Text style={styles.primaryText}>{button}</Text>
        </Pressable>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  header: {
    alignItems: 'center',
    borderBottomColor: colors.divider,
    borderBottomWidth: 1,
    flexDirection: 'row',
    padding: 16,
  },
  headerCopy: { flex: 1, marginLeft: 10 },
  eyebrow: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  headerTitle: { color: colors.textPrimary, fontSize: 21, fontWeight: '900' },
  content: { padding: 18, paddingBottom: 42 },
  hero: { backgroundColor: colors.primarySoft, borderRadius: 18, padding: 18 },
  heroBadge: { color: colors.primary, fontSize: 12, fontWeight: '800' },
  heroTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: '900', marginTop: 8 },
  heroDescription: { color: colors.textSecondary, fontSize: 13, lineHeight: 20, marginTop: 7 },
  tourApiBadge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: colors.seaSoftLight,
    borderRadius: 10,
    flexDirection: 'row',
    gap: 5,
    marginTop: 10,
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  tourApiBadgeText: { color: colors.seaDeep, fontSize: 11, fontWeight: '800' },
  dayScroller: { marginVertical: 18 },
  dayTab: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    borderRadius: 12,
    marginRight: 8,
    minWidth: 72,
    padding: 10,
  },
  dayTabActive: { backgroundColor: colors.sea },
  dayText: { color: colors.textSecondary, fontSize: 13, fontWeight: '800' },
  dayTextActive: { color: colors.surface },
  dayDate: { color: colors.textTertiary, fontSize: 10, marginTop: 3 },
  sectionTitle: { color: colors.textPrimary, fontSize: 19, fontWeight: '900', marginBottom: 10 },
  itemCard: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 15,
    borderWidth: 1,
    flexDirection: 'row',
    marginBottom: 10,
    padding: 10,
  },
  itemMain: { alignItems: 'center', flex: 1, flexDirection: 'row' },
  itemMainPressed: { opacity: 0.7 },
  thumbnail: { borderRadius: 11, height: 72, width: 72 },
  thumbnailPlaceholder: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    justifyContent: 'center',
  },
  itemCopy: { flex: 1, paddingHorizontal: 10 },
  itemTime: { color: colors.primary, fontSize: 11, fontWeight: '800' },
  itemName: { color: colors.textPrimary, fontSize: 15, fontWeight: '900', marginTop: 2 },
  itemReason: { color: colors.textSecondary, fontSize: 11, lineHeight: 16, marginTop: 4 },
  scoreText: { color: colors.seaDeep, fontSize: 10, fontWeight: '700', marginTop: 5 },
  itemActions: { alignItems: 'center', gap: 18 },
  itemCardUnfilled: { borderStyle: 'dashed' },
  itemNameMuted: { color: colors.textSecondary },
  verifyChip: {
    backgroundColor: colors.primarySoft,
    borderRadius: 7,
    color: colors.primaryDeep,
    fontSize: 10,
    fontWeight: '800',
    overflow: 'hidden',
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  candidateBox: {
    borderColor: colors.divider,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 10,
    marginLeft: 14,
    marginTop: -4,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  candidateHeader: { color: colors.textTertiary, fontSize: 11, fontWeight: '800', marginBottom: 2 },
  candidateRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    paddingVertical: 7,
  },
  candidateTitleRow: { alignItems: 'center', flexDirection: 'row', gap: 6 },
  candidateName: { color: colors.textPrimary, flexShrink: 1, fontSize: 13, fontWeight: '800' },
  slotBadge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: colors.primarySoft,
    borderRadius: 10,
    flexDirection: 'row',
    gap: 5,
    marginTop: 8,
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  slotBadgeText: { color: colors.primaryDeep, fontSize: 11, fontWeight: '800' },
  emptyText: { color: colors.textSecondary, paddingVertical: 30, textAlign: 'center' },
  addButton: {
    alignItems: 'center',
    borderColor: colors.seaDeep,
    borderRadius: 13,
    borderStyle: 'dashed',
    borderWidth: 1,
    flexDirection: 'row',
    gap: 7,
    justifyContent: 'center',
    marginBottom: 8,
    minHeight: 48,
  },
  addButtonText: { color: colors.seaDeep, fontSize: 13, fontWeight: '800' },
  tourApiSection: { marginTop: 16 },
  tourApiSectionTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '900' },
  tourApiSectionDescription: {
    color: colors.textSecondary,
    fontSize: 11,
    marginBottom: 9,
    marginTop: 4,
  },
  tourApiCard: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 13,
    borderWidth: 1,
    flexDirection: 'row',
    marginBottom: 8,
    padding: 9,
  },
  tourApiImage: { borderRadius: 10, height: 60, width: 60 },
  feedback: {
    backgroundColor: colors.seaSoftLight,
    borderRadius: 10,
    color: colors.seaDeep,
    fontSize: 12,
    marginTop: 8,
    padding: 12,
  },
  primaryButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 13,
    justifyContent: 'center',
    marginTop: 14,
    minHeight: 50,
    paddingHorizontal: 16,
  },
  primaryText: { color: colors.surface, fontSize: 14, fontWeight: '900' },
  disabled: { opacity: 0.4 },
  modalBackdrop: { backgroundColor: overlayColors.scrim, flex: 1, justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    maxHeight: '85%',
    padding: 20,
  },
  sheetHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  sheetTitle: { color: colors.textPrimary, fontSize: 19, fontWeight: '900' },
  methodButton: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 14,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    marginBottom: 10,
    padding: 15,
  },
  methodTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '800' },
  methodDescription: { color: colors.textSecondary, fontSize: 11, marginTop: 3 },
  textArea: {
    borderColor: colors.divider,
    borderRadius: 12,
    borderWidth: 1,
    minHeight: 105,
    padding: 12,
    textAlignVertical: 'top',
  },
  interpretation: { color: colors.seaDeep, fontSize: 12, fontWeight: '700', marginVertical: 12 },
  searchRow: { flexDirection: 'row', gap: 8 },
  searchInput: {
    borderColor: colors.divider,
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    minHeight: 48,
    paddingHorizontal: 12,
  },
  searchButton: {
    alignItems: 'center',
    backgroundColor: colors.seaDeep,
    borderRadius: 12,
    justifyContent: 'center',
    width: 48,
  },
  timeRow: { marginBottom: 12 },
  timeLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: '700', marginBottom: 6 },
  timeHelp: { color: colors.textSecondary, fontSize: 12, marginBottom: 8 },
  timeInput: {
    borderColor: colors.divider,
    borderRadius: 12,
    borderWidth: 1,
    fontSize: 16,
    minHeight: 48,
    paddingHorizontal: 12,
  },
  resultRow: {
    alignItems: 'center',
    borderBottomColor: colors.divider,
    borderBottomWidth: 1,
    flexDirection: 'row',
    minHeight: 65,
  },
  replaceText: { color: colors.primary, fontSize: 13, fontWeight: '800' },
  error: { color: colors.error, fontSize: 12, marginTop: 12 },
  state: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    flex: 1,
    justifyContent: 'center',
    padding: 28,
  },
  stateTitle: {
    color: colors.textPrimary,
    fontSize: 21,
    fontWeight: '900',
    marginTop: 16,
    textAlign: 'center',
  },
  stateDescription: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
    marginTop: 8,
    textAlign: 'center',
  },
  stateButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 13,
    marginTop: 20,
    minWidth: 150,
    padding: 14,
  },
});

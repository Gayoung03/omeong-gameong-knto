import Ionicons from '@expo/vector-icons/Ionicons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { recommendedDays } from '../mocks/routes.mock';
import { RouteBottomNavigation } from '../components/RouteBottomNavigation';
import type { RoutePlace } from '../types';
import {
  formatRouteDate,
  formatTripDuration,
  getTripDates,
} from '../utils/tripDuration';

const palette = {
  orange: '#FF7A00',
  mint: '#12B89B',
  deepMint: '#0C9E86',
  ink: '#292B2E',
  gray: '#72777F',
  lightGray: '#F4F5F6',
  line: '#E7E9EB',
  warning: '#E99A2C',
  white: '#FFFFFF',
};

const formatTravelMinutes = (minutes: number) => {
  if (minutes <= 0) return '이동 없음';
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (hours === 0) return `약 ${remainder}분`;
  return remainder === 0 ? `약 ${hours}시간` : `약 ${hours}시간 ${remainder}분`;
};

function SelectionCircle({ selected }: { selected: boolean }) {
  return (
    <View style={[styles.selectionCircle, selected && styles.selectionCircleSelected]}>
      {selected ? <Ionicons color={palette.white} name="checkmark" size={14} /> : null}
    </View>
  );
}

function PlaceCard({
  index,
  place,
  selected,
  onPress,
}: {
  index: number;
  place: RoutePlace;
  selected: boolean;
  onPress: () => void;
}) {
  const needsCheck = place.petStatus === '확인 필요';

  return (
    <View>
      {place.travelMinutes ? (
        <View style={styles.travelRow}>
          <View style={styles.timelineLine} />
          <Ionicons color="#A1A6AC" name="car-outline" size={14} />
          <Text style={styles.travelText}>차량 {place.travelMinutes}분</Text>
        </View>
      ) : null}

      <Pressable
        accessibilityLabel={`${place.name} 일정 ${selected ? '선택 해제' : '선택'}`}
        onPress={onPress}
        style={({ pressed }) => [styles.placeCard, pressed && styles.pressed]}
        testID={`place-card-${place.id}`}
      >
        <View style={styles.timelineColumn}>
          <View style={styles.timelineDot} />
          <Text style={styles.timeText}>{place.time}</Text>
        </View>

        <View style={[styles.thumbnail, { backgroundColor: place.thumbnailColor }]}>
          <Text style={styles.thumbnailEmoji}>{place.emoji}</Text>
        </View>

        <View style={styles.placeContent}>
          <View style={styles.placeTitleRow}>
            <Text numberOfLines={1} style={styles.placeName}>
              {place.name}
            </Text>
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>{place.category}</Text>
            </View>
          </View>
          <Text numberOfLines={2} style={styles.placeSubtitle}>
            {place.subtitle}
          </Text>
          <View style={[styles.petBadge, needsCheck && styles.petBadgeWarning]}>
            <Ionicons
              color={needsCheck ? palette.warning : palette.deepMint}
              name={needsCheck ? 'alert-circle-outline' : 'paw-outline'}
              size={13}
            />
            <Text style={[styles.petBadgeText, needsCheck && styles.petBadgeTextWarning]}>
              {place.petStatus}
            </Text>
          </View>
        </View>

        <View style={styles.cardSelection}>
          <Text style={styles.orderText}>{index + 1}</Text>
          <SelectionCircle selected={selected} />
        </View>
      </Pressable>
    </View>
  );
}

export function RouteRecommendationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    petName?: string;
    tripTitle?: string;
    startAt?: string;
    endAt?: string;
    pace?: string;
    selectedPlaces?: string;
  }>();
  const tripDays = useMemo(() => {
    if (!params.startAt || !params.endAt) return recommendedDays;

    return getTripDates(params.startAt, params.endAt).map((date, index) => {
      const mockDay = recommendedDays[index % recommendedDays.length];
      return {
        ...mockDay,
        day: index + 1,
        date: formatRouteDate(date),
        places: mockDay.places.map((place) => ({
          ...place,
          id: `${place.id}-day-${index + 1}`,
        })),
      };
    });
  }, [params.endAt, params.startAt]);

  const [selectedDay, setSelectedDay] = useState(1);
  const [selectedPlaceIds, setSelectedPlaceIds] = useState<string[]>(
    () => tripDays.flatMap((day) => day.places.map((place) => place.id)),
  );
  const [feedback, setFeedback] = useState<string | null>(null);
  const [openModal, setOpenModal] = useState<'map' | 'saved' | 'request' | null>(null);
  const [requestText, setRequestText] = useState('');

  const duration = params.startAt && params.endAt
    ? formatTripDuration(params.startAt, params.endAt)
    : `${recommendedDays.length - 1}박 ${recommendedDays.length}일`;

  const activeDay = tripDays[selectedDay - 1];
  const activeIds = useMemo(() => activeDay.places.map((place) => place.id), [activeDay]);
  const allActiveSelected = activeIds.every((id) => selectedPlaceIds.includes(id));

  const togglePlace = (placeId: string) => {
    setFeedback(null);
    setSelectedPlaceIds((current) =>
      current.includes(placeId)
        ? current.filter((id) => id !== placeId)
        : [...current, placeId],
    );
  };

  const toggleAllForDay = () => {
    setFeedback(null);
    setSelectedPlaceIds((current) => {
      if (allActiveSelected) {
        return current.filter((id) => !activeIds.includes(id));
      }

      return [...new Set([...current, ...activeIds])];
    });
  };

  const selectedCount = selectedPlaceIds.length;
  const activeSelectedPlaces = activeDay.places.filter((place) =>
    selectedPlaceIds.includes(place.id),
  );
  const activeTravelMinutes = activeSelectedPlaces.reduce(
    (total, place, index) => total + (index === 0 ? 0 : (place.travelMinutes ?? 0)),
    0,
  );
  const shareRoute = async () => {
    const itinerary = tripDays
      .map((day) => {
        const places = day.places.filter((place) => selectedPlaceIds.includes(place.id));
        if (places.length === 0) return '';
        return `${day.day}일차 · ${day.date}\n${places.map((place) => `${place.time} ${place.name}`).join('\n')}`;
      })
      .filter(Boolean)
      .join('\n\n');
    const message = `${params.petName ?? '몽이'}와 함께하는 ${duration} ${params.tripTitle ?? '제주 여행'}\n\n${itinerary}`;

    try {
      if (Platform.OS === 'web' && typeof navigator !== 'undefined') {
        if (navigator.share) {
          await navigator.share({ title: '오멍가멍 추천 코스', text: message });
        } else {
          await navigator.clipboard.writeText(message);
          setFeedback('추천 코스를 클립보드에 복사했어요.');
        }
        return;
      }

      await Share.share({ message, title: '오멍가멍 추천 코스' });
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        setFeedback('공유 기능을 실행하지 못했어요. 다시 시도해주세요.');
      }
    }
  };

  const saveRoute = async () => {
    try {
      await AsyncStorage.setItem(
        'saved-recommended-route',
        JSON.stringify({
          savedAt: new Date().toISOString(),
          tripTitle: params.tripTitle ?? '제주 여행',
          startAt: params.startAt,
          endAt: params.endAt,
          duration,
          pace: params.pace ?? '여유롭게',
          petName: params.petName ?? '몽이',
          selectedPlaces: params.selectedPlaces?.split(',').filter(Boolean) ?? [],
          days: tripDays.map((day) => ({
            date: day.date,
            day: day.day,
            places: day.places
              .filter((place) => selectedPlaceIds.includes(place.id))
              .map((place, index, places) => ({
                id: place.id,
                name: place.name,
                order: index + 1,
                time: place.time,
                travelMinutes: index === 0 ? 0 : (place.travelMinutes ?? 0),
              })),
          })),
        }),
      );
      setOpenModal('saved');
    } catch {
      setFeedback('코스를 저장하지 못했어요. 다시 시도해주세요.');
    }
  };

  const submitChangeRequest = () => {
    const request = requestText.trim();
    if (!request) return;
    setOpenModal(null);
    setRequestText('');
    setFeedback(`혼디가 “${request}” 요청을 반영해 새 코스를 준비할게요.`);
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.header}>
        <View style={styles.headerTitleGroup}>
          <Pressable accessibilityLabel="정보 입력으로 돌아가기" onPress={() => router.back()}>
            <Ionicons color={palette.ink} name="chevron-back" size={24} />
          </Pressable>
          <View>
            <Text style={styles.eyebrow}>AI 맞춤 여행 플래너</Text>
            <Text style={styles.headerTitle}>추천 결과</Text>
          </View>
        </View>
        <Pressable
          accessibilityLabel="추천 결과 공유"
          onPress={() => void shareRoute()}
          style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
        >
          <Ionicons color={palette.ink} name="share-outline" size={22} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.heroCard}>
          <View style={styles.heroCopy}>
            <View style={styles.recommendationBadge}>
              <Ionicons color={palette.orange} name="sparkles" size={13} />
              <Text style={styles.recommendationBadgeText}>혼디 추천 코스</Text>
            </View>
            <Text style={styles.heroTitle}>
              {params.petName ?? '몽이'}와 함께하는 {duration} {params.tripTitle ?? '제주 여행'}
            </Text>
            <Text style={styles.heroDescription}>
              {params.pace ?? '여유롭게'} 여행하도록 날씨와 이동 동선을 고려했어요.
            </Text>
          </View>
          <View style={styles.petIllustration}>
            <View style={styles.illustrationSun} />
            <Text style={styles.petEmoji}>🐶</Text>
          </View>
        </View>

        <View style={styles.summaryChips}>
          <View style={styles.summaryChip}>
            <Text style={styles.summaryEmoji}>🌤️</Text>
            <Text style={styles.summaryText}>날씨 반영</Text>
          </View>
          <View style={styles.summaryChip}>
            <Text style={styles.summaryEmoji}>🐾</Text>
            <Text style={styles.summaryText}>반려동물 동반 가능</Text>
          </View>
          <View style={styles.summaryChip}>
            <Text style={styles.summaryEmoji}>🌿</Text>
            <Text style={styles.summaryText}>실내·실외 균형</Text>
          </View>
        </View>

        <View accessibilityRole="tablist" style={styles.dayTabs}>
          {tripDays.map((day) => {
            const active = day.day === selectedDay;
            return (
              <Pressable
                accessibilityRole="tab"
                accessibilityState={{ selected: active }}
                key={day.day}
                onPress={() => {
                  setSelectedDay(day.day);
                  setFeedback(null);
                }}
                style={[styles.dayTab, active && styles.dayTabActive]}
                testID={`day-tab-${day.day}`}
              >
                <Text style={[styles.dayTabTitle, active && styles.dayTabTitleActive]}>
                  {day.day}일차
                </Text>
                <Text style={[styles.dayTabDate, active && styles.dayTabDateActive]}>
                  {day.date}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>{selectedDay}일차 일정</Text>
            <View style={styles.weatherRow}>
              <Text style={styles.weatherText}>{activeDay.weather}</Text>
              <View style={styles.weatherDivider} />
              <Text style={styles.weatherText}>{activeDay.temperature}</Text>
            </View>
          </View>
          <Pressable
            accessibilityLabel={`${selectedDay}일차 전체 ${allActiveSelected ? '선택 해제' : '선택'}`}
            onPress={toggleAllForDay}
            style={({ pressed }) => [styles.selectAllButton, pressed && styles.pressed]}
            testID="select-all-button"
          >
            <SelectionCircle selected={allActiveSelected} />
            <Text style={styles.selectAllText}>전체 선택</Text>
          </Pressable>
        </View>

        <View style={styles.placeList}>
          {activeDay.places.map((place, index) => (
            <PlaceCard
              index={index}
              key={place.id}
              onPress={() => togglePlace(place.id)}
              place={place}
              selected={selectedPlaceIds.includes(place.id)}
            />
          ))}
        </View>

        <View style={styles.routeSummary}>
          <View style={styles.routeStops}>
            {activeSelectedPlaces.map((place, index) => (
              <View key={place.id} style={styles.routeStopWrap}>
                <View style={[styles.routeStop, { backgroundColor: place.thumbnailColor }]}>
                  <Text style={styles.routeStopEmoji}>{place.emoji}</Text>
                </View>
                {index < activeSelectedPlaces.length - 1 ? (
                  <Ionicons color="#B4B8BC" name="arrow-forward" size={14} />
                ) : null}
              </View>
            ))}
          </View>
          <View style={styles.routeSummaryCopy}>
            <Text style={styles.routeSummaryTitle}>총 이동 {formatTravelMinutes(activeTravelMinutes)}</Text>
            <Text style={styles.routeSummaryText}>
              선택한 {activeSelectedPlaces.length}개 장소를 기준으로 계산했어요.
            </Text>
          </View>
        </View>

        {feedback ? (
          <View accessibilityRole="alert" style={styles.feedbackBanner} testID="feedback-banner">
            <Ionicons color={palette.deepMint} name="checkmark-circle" size={18} />
            <Text style={styles.feedbackText}>{feedback}</Text>
          </View>
        ) : null}

        <View style={styles.actionRow}>
          <Pressable
            accessibilityRole="button"
            disabled={activeSelectedPlaces.length === 0}
            onPress={() => setOpenModal('map')}
            style={({ pressed }) => [
              styles.secondaryButton,
              activeSelectedPlaces.length === 0 && styles.buttonDisabled,
              pressed && styles.pressed,
            ]}
            testID="map-button"
          >
            <Ionicons color={palette.ink} name="map-outline" size={18} />
            <Text style={styles.secondaryButtonText}>지도 보기</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            disabled={selectedCount === 0}
            onPress={() => void saveRoute()}
            style={({ pressed }) => [
              styles.primaryButton,
              selectedCount === 0 && styles.buttonDisabled,
              pressed && styles.pressed,
            ]}
            testID="save-route-button"
          >
            <Ionicons color={palette.white} name="bookmark-outline" size={18} />
            <Text style={styles.primaryButtonText}>코스 저장하기</Text>
          </Pressable>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => setOpenModal('request')}
          style={({ pressed }) => [styles.aiRequestCard, pressed && styles.pressed]}
          testID="request-change-button"
        >
          <View style={styles.aiIcon}>
            <Text style={styles.aiIconEmoji}>🐶</Text>
          </View>
          <View style={styles.aiRequestCopy}>
            <Text style={styles.aiRequestTitle}>일정이 마음에 들지 않나요?</Text>
            <Text style={styles.aiRequestText}>혼디에게 원하는 방식으로 수정을 요청해보세요.</Text>
          </View>
          <Ionicons color={palette.orange} name="chevron-forward" size={20} />
        </Pressable>
      </ScrollView>

      <RouteBottomNavigation />

      <Modal
        animationType="fade"
        onRequestClose={() => setOpenModal(null)}
        transparent
        visible={openModal !== null}
      >
        <View style={styles.modalBackdrop}>
          <Pressable onPress={() => setOpenModal(null)} style={styles.modalDismissArea} />
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {openModal === 'map'
                  ? `${selectedDay}일차 경로`
                  : openModal === 'saved'
                    ? '코스 저장 완료'
                    : '혼디에게 수정 요청'}
              </Text>
              <Pressable accessibilityLabel="닫기" onPress={() => setOpenModal(null)}>
                <Ionicons color={palette.gray} name="close" size={23} />
              </Pressable>
            </View>

            {openModal === 'map' ? (
              <View>
                <View style={styles.mockMap}>
                  <View style={styles.mapRoad} />
                  {activeSelectedPlaces.map((place, index) => (
                    <View
                      key={place.id}
                      style={[
                        styles.mapPin,
                        {
                          left: `${14 + index * (70 / Math.max(activeSelectedPlaces.length - 1, 1))}%`,
                          top: index % 2 === 0 ? 48 : 82,
                        },
                      ]}
                    >
                      <Text style={styles.mapPinNumber}>{index + 1}</Text>
                    </View>
                  ))}
                  <View style={styles.mapCompass}>
                    <Ionicons color={palette.orange} name="navigate" size={18} />
                  </View>
                </View>
                <View style={styles.mapPlaceList}>
                  {activeSelectedPlaces.map((place, index) => (
                    <View key={place.id} style={styles.mapPlaceRow}>
                      <View style={styles.mapPlaceNumber}><Text style={styles.mapPlaceNumberText}>{index + 1}</Text></View>
                      <Text style={styles.mapPlaceName}>{place.name}</Text>
                      <Text style={styles.mapPlaceTime}>{place.time}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ) : null}

            {openModal === 'saved' ? (
              <View style={styles.savedContent}>
                <View style={styles.savedIcon}>
                  <Ionicons color={palette.deepMint} name="checkmark" size={31} />
                </View>
                <Text style={styles.savedTitle}>{selectedCount}개 장소를 저장했어요</Text>
                <Text style={styles.savedText}>저장한 코스는 내 여행에서 다시 확인할 수 있어요.</Text>
                <Pressable
                  onPress={() => {
                    setOpenModal(null);
                    router.replace('/trips');
                  }}
                  style={styles.modalPrimaryButton}
                >
                  <Text style={styles.modalPrimaryText}>내 여행에서 확인</Text>
                </Pressable>
              </View>
            ) : null}

            {openModal === 'request' ? (
              <View>
                <Text style={styles.requestGuide}>
                  바꾸고 싶은 장소나 일정 조건을 자연스럽게 적어주세요.
                </Text>
                <View style={styles.requestExamples}>
                  {['카페를 한 곳 더 넣어줘', '비 오는 날 실내 위주로 바꿔줘', '이동 시간을 줄여줘'].map(
                    (example) => (
                      <Pressable key={example} onPress={() => setRequestText(example)} style={styles.requestChip}>
                        <Text style={styles.requestChipText}>{example}</Text>
                      </Pressable>
                    ),
                  )}
                </View>
                <TextInput
                  multiline
                  onChangeText={setRequestText}
                  placeholder="예: 둘째 날 카페 대신 바다 산책 코스를 넣어줘"
                  placeholderTextColor="#A4A8AD"
                  style={styles.requestInput}
                  value={requestText}
                />
                <Pressable
                  disabled={!requestText.trim()}
                  onPress={submitChangeRequest}
                  style={[styles.modalPrimaryButton, !requestText.trim() && styles.buttonDisabled]}
                >
                  <Text style={styles.modalPrimaryText}>수정 요청 보내기</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    alignSelf: 'center',
    backgroundColor: palette.white,
    flex: 1,
    maxWidth: 430,
    width: '100%',
  },
  header: {
    alignItems: 'center',
    backgroundColor: palette.white,
    borderBottomColor: '#F1F2F3',
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  headerTitleGroup: { alignItems: 'center', flexDirection: 'row', gap: 7 },
  eyebrow: { color: palette.orange, fontSize: 11, fontWeight: '700', marginBottom: 2 },
  headerTitle: { color: palette.ink, fontSize: 21, fontWeight: '800' },
  iconButton: {
    alignItems: 'center',
    borderColor: palette.line,
    borderRadius: 18,
    borderWidth: 1,
    height: 38,
    justifyContent: 'center',
    width: 38,
  },
  scrollContent: { paddingBottom: 36, paddingHorizontal: 18, paddingTop: 16 },
  heroCard: {
    alignItems: 'center',
    backgroundColor: '#FFF6E9',
    borderColor: '#FFE5C3',
    borderRadius: 20,
    borderWidth: 1,
    flexDirection: 'row',
    minHeight: 138,
    overflow: 'hidden',
    padding: 18,
  },
  heroCopy: { flex: 1, paddingRight: 8 },
  recommendationBadge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: palette.white,
    borderRadius: 999,
    flexDirection: 'row',
    gap: 5,
    marginBottom: 10,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  recommendationBadgeText: { color: palette.orange, fontSize: 11, fontWeight: '800' },
  heroTitle: { color: palette.ink, fontSize: 18, fontWeight: '800', lineHeight: 25 },
  heroDescription: { color: palette.gray, fontSize: 12, lineHeight: 18, marginTop: 6 },
  petIllustration: {
    alignItems: 'center',
    backgroundColor: '#FFE0B5',
    borderRadius: 44,
    height: 82,
    justifyContent: 'center',
    position: 'relative',
    width: 82,
  },
  illustrationSun: {
    backgroundColor: '#FFB349',
    borderRadius: 13,
    height: 26,
    position: 'absolute',
    right: 2,
    top: 2,
    width: 26,
  },
  petEmoji: { fontSize: 46 },
  summaryChips: { flexDirection: 'row', gap: 7, marginTop: 12 },
  summaryChip: {
    alignItems: 'center',
    backgroundColor: '#F1FBF8',
    borderColor: '#D7F1EA',
    borderRadius: 999,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: 6,
  },
  summaryEmoji: { fontSize: 12, marginRight: 3 },
  summaryText: { color: palette.deepMint, fontSize: 10, fontWeight: '700' },
  dayTabs: {
    backgroundColor: palette.lightGray,
    borderRadius: 14,
    flexDirection: 'row',
    marginTop: 18,
    padding: 4,
  },
  dayTab: { alignItems: 'center', borderRadius: 11, flex: 1, paddingVertical: 8 },
  dayTabActive: { backgroundColor: palette.mint },
  dayTabTitle: { color: '#777C82', fontSize: 13, fontWeight: '700' },
  dayTabTitleActive: { color: palette.white },
  dayTabDate: { color: '#A4A8AD', fontSize: 9, marginTop: 2 },
  dayTabDateActive: { color: '#DFFFF8' },
  sectionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
    marginTop: 22,
  },
  sectionTitle: { color: palette.ink, fontSize: 18, fontWeight: '800' },
  weatherRow: { alignItems: 'center', flexDirection: 'row', marginTop: 5 },
  weatherText: { color: palette.gray, fontSize: 11, fontWeight: '600' },
  weatherDivider: { backgroundColor: '#D5D8DB', height: 10, marginHorizontal: 7, width: 1 },
  selectAllButton: { alignItems: 'center', flexDirection: 'row', gap: 6, paddingVertical: 7 },
  selectAllText: { color: palette.gray, fontSize: 12, fontWeight: '700' },
  selectionCircle: {
    alignItems: 'center',
    borderColor: '#CED2D6',
    borderRadius: 10,
    borderWidth: 1.5,
    height: 20,
    justifyContent: 'center',
    width: 20,
  },
  selectionCircleSelected: { backgroundColor: palette.mint, borderColor: palette.mint },
  placeList: { paddingBottom: 4 },
  travelRow: { alignItems: 'center', flexDirection: 'row', height: 28, marginLeft: 19 },
  timelineLine: { backgroundColor: '#D9ECE7', height: 28, marginRight: 13, width: 2 },
  travelText: { color: '#92979D', fontSize: 10, marginLeft: 4 },
  placeCard: {
    alignItems: 'center',
    backgroundColor: palette.white,
    borderColor: palette.line,
    borderRadius: 15,
    borderWidth: 1,
    flexDirection: 'row',
    minHeight: 104,
    padding: 10,
    shadowColor: '#111111',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
  },
  timelineColumn: { alignItems: 'center', alignSelf: 'stretch', paddingTop: 8, width: 42 },
  timelineDot: {
    backgroundColor: palette.orange,
    borderColor: '#FFE7CD',
    borderRadius: 6,
    borderWidth: 3,
    height: 12,
    width: 12,
  },
  timeText: { color: palette.ink, fontSize: 10, fontWeight: '800', marginTop: 7 },
  thumbnail: { alignItems: 'center', borderRadius: 12, height: 76, justifyContent: 'center', width: 76 },
  thumbnailEmoji: { fontSize: 32 },
  placeContent: { flex: 1, paddingHorizontal: 11 },
  placeTitleRow: { alignItems: 'center', flexDirection: 'row', gap: 6 },
  placeName: { color: palette.ink, flexShrink: 1, fontSize: 14, fontWeight: '800' },
  categoryBadge: { backgroundColor: '#F2F3F4', borderRadius: 5, paddingHorizontal: 5, paddingVertical: 3 },
  categoryText: { color: '#777C82', fontSize: 8, fontWeight: '700' },
  placeSubtitle: { color: palette.gray, fontSize: 10, lineHeight: 15, marginTop: 4 },
  petBadge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: '#EAF8F4',
    borderRadius: 6,
    flexDirection: 'row',
    gap: 3,
    marginTop: 7,
    paddingHorizontal: 6,
    paddingVertical: 4,
  },
  petBadgeWarning: { backgroundColor: '#FFF4E3' },
  petBadgeText: { color: palette.deepMint, fontSize: 9, fontWeight: '800' },
  petBadgeTextWarning: { color: palette.warning },
  cardSelection: { alignItems: 'center', alignSelf: 'stretch', justifyContent: 'space-between' },
  orderText: { color: '#B5B9BD', fontSize: 10, fontWeight: '700' },
  routeSummary: {
    backgroundColor: '#F6FAF9',
    borderColor: '#DDEEEA',
    borderRadius: 15,
    borderWidth: 1,
    marginTop: 14,
    padding: 14,
  },
  routeStops: { alignItems: 'center', flexDirection: 'row', marginBottom: 10 },
  routeStopWrap: { alignItems: 'center', flex: 1, flexDirection: 'row' },
  routeStop: { alignItems: 'center', borderRadius: 15, height: 30, justifyContent: 'center', width: 30 },
  routeStopEmoji: { fontSize: 14 },
  routeSummaryCopy: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  routeSummaryTitle: { color: palette.ink, fontSize: 12, fontWeight: '800' },
  routeSummaryText: { color: palette.gray, fontSize: 10, marginTop: 2 },
  feedbackBanner: {
    alignItems: 'center',
    backgroundColor: '#EAF9F5',
    borderRadius: 12,
    flexDirection: 'row',
    gap: 7,
    marginTop: 12,
    padding: 12,
  },
  feedbackText: { color: '#157C6B', flex: 1, fontSize: 11, fontWeight: '700' },
  actionRow: { flexDirection: 'row', gap: 9, marginTop: 16 },
  secondaryButton: {
    alignItems: 'center',
    borderColor: '#D8DBDE',
    borderRadius: 13,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: 7,
    justifyContent: 'center',
    minHeight: 49,
  },
  secondaryButtonText: { color: palette.ink, fontSize: 13, fontWeight: '800' },
  primaryButton: {
    alignItems: 'center',
    backgroundColor: palette.orange,
    borderRadius: 13,
    flex: 1.35,
    flexDirection: 'row',
    gap: 7,
    justifyContent: 'center',
    minHeight: 49,
  },
  primaryButtonText: { color: palette.white, fontSize: 13, fontWeight: '800' },
  buttonDisabled: { backgroundColor: '#C8CBCF' },
  aiRequestCard: {
    alignItems: 'center',
    backgroundColor: '#FFF7ED',
    borderColor: '#FFE2C0',
    borderRadius: 15,
    borderWidth: 1,
    flexDirection: 'row',
    marginTop: 12,
    padding: 13,
  },
  aiIcon: {
    alignItems: 'center',
    backgroundColor: '#FFE5C3',
    borderRadius: 20,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  aiIconEmoji: { fontSize: 22 },
  aiRequestCopy: { flex: 1, paddingHorizontal: 10 },
  aiRequestTitle: { color: palette.ink, fontSize: 12, fontWeight: '800' },
  aiRequestText: { color: palette.gray, fontSize: 10, lineHeight: 15, marginTop: 3 },
  modalBackdrop: { alignItems: 'center', backgroundColor: '#00000066', flex: 1, justifyContent: 'center', padding: 18 },
  modalDismissArea: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  modalCard: { backgroundColor: palette.white, borderRadius: 20, maxWidth: 398, padding: 18, width: '100%' },
  modalHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 15 },
  modalTitle: { color: palette.ink, fontSize: 18, fontWeight: '900' },
  mockMap: { backgroundColor: '#EAF4E8', borderRadius: 15, height: 170, overflow: 'hidden', position: 'relative' },
  mapRoad: { backgroundColor: '#FFF9E9', borderColor: '#D7CBAA', borderRadius: 30, borderWidth: 2, height: 48, left: 20, position: 'absolute', right: 18, top: 62, transform: [{ rotate: '-8deg' }] },
  mapPin: { alignItems: 'center', backgroundColor: palette.orange, borderColor: palette.white, borderRadius: 14, borderWidth: 3, height: 28, justifyContent: 'center', position: 'absolute', width: 28 },
  mapPinNumber: { color: palette.white, fontSize: 10, fontWeight: '900' },
  mapCompass: { alignItems: 'center', backgroundColor: palette.white, borderRadius: 18, bottom: 10, height: 36, justifyContent: 'center', position: 'absolute', right: 10, width: 36 },
  mapPlaceList: { gap: 7, marginTop: 12 },
  mapPlaceRow: { alignItems: 'center', borderBottomColor: palette.line, borderBottomWidth: 1, flexDirection: 'row', minHeight: 34, paddingBottom: 7 },
  mapPlaceNumber: { alignItems: 'center', backgroundColor: '#FFF0DE', borderRadius: 10, height: 21, justifyContent: 'center', width: 21 },
  mapPlaceNumberText: { color: palette.orange, fontSize: 9, fontWeight: '900' },
  mapPlaceName: { color: palette.ink, flex: 1, fontSize: 11, fontWeight: '700', paddingHorizontal: 8 },
  mapPlaceTime: { color: palette.gray, fontSize: 10 },
  savedContent: { alignItems: 'center', paddingTop: 3 },
  savedIcon: { alignItems: 'center', backgroundColor: '#E7F8F3', borderRadius: 31, height: 62, justifyContent: 'center', width: 62 },
  savedTitle: { color: palette.ink, fontSize: 16, fontWeight: '900', marginTop: 13 },
  savedText: { color: palette.gray, fontSize: 10, marginBottom: 16, marginTop: 5, textAlign: 'center' },
  requestGuide: { color: palette.gray, fontSize: 11, lineHeight: 17 },
  requestExamples: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 11 },
  requestChip: { backgroundColor: '#FFF4E7', borderRadius: 999, paddingHorizontal: 9, paddingVertical: 7 },
  requestChipText: { color: palette.orange, fontSize: 9, fontWeight: '700' },
  requestInput: { borderColor: palette.line, borderRadius: 12, borderWidth: 1, color: palette.ink, fontSize: 11, marginBottom: 11, marginTop: 12, minHeight: 100, outlineStyle: 'none', padding: 11, textAlignVertical: 'top' } as never,
  modalPrimaryButton: { alignItems: 'center', alignSelf: 'stretch', backgroundColor: palette.orange, borderRadius: 11, justifyContent: 'center', minHeight: 46 },
  modalPrimaryText: { color: palette.white, fontSize: 12, fontWeight: '900' },
  pressed: { opacity: 0.72 },
});

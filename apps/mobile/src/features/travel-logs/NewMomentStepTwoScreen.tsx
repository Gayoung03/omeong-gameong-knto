import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Avatar } from '@/src/components/ui/Avatar';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { useAllPets, usePets } from '@/src/features/profile/hooks/usePets';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';
import type { Trip } from '@/src/types/travelLog';

import {
  MomentPetSelectionSheet,
  type MomentPetSelectionSheetHandle,
} from './components/MomentPetSelectionSheet';
import { MomentStepHeader } from './components/MomentStepHeader';
import { mockLogs, mockTrips } from './mocks/travelLogMocks';
import { useLogDraftStore } from './stores/useLogDraftStore';
import { resolveCompanions, toPetsById } from './utils/resolveCompanionDisplay';

type CoursePlace = {
  placeId: string;
  name: string;
  date: string;
  period: string;
  day: number;
};

const now = new Date();
const TODAY = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
const DIRECT_PLACES: CoursePlace[] = [
  { placeId: 'direct-1', name: '제주 반려동물 공원', date: TODAY, period: '오후', day: 1 },
  { placeId: 'direct-2', name: '도두 무지개 해안도로', date: TODAY, period: '오전', day: 1 },
  { placeId: 'direct-3', name: '함덕해수욕장', date: TODAY, period: '오후', day: 1 },
];

function minusOneMonth(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00`);
  date.setMonth(date.getMonth() - 1);
  return date.toISOString().slice(0, 10);
}

function formatRange(trip: Trip): string {
  return `${trip.startDate.replaceAll('-', '.')} – ${trip.endDate.slice(5).replace('-', '.')}`;
}

function placesForTrip(trip: Trip): CoursePlace[] {
  const seen = new Set<string>();
  return mockLogs
    .filter((log) => log.tripId === trip.tripId && log.placeId)
    .sort((a, b) => a.recordedDate.localeCompare(b.recordedDate))
    .filter((log) => {
      if (!log.placeId || seen.has(log.placeId)) return false;
      seen.add(log.placeId);
      return true;
    })
    .slice(0, 5)
    .map((log) => {
      const hour = Number(log.visitedAt?.slice(11, 13) ?? 12);
      const start = new Date(`${trip.startDate}T00:00:00`);
      const visit = new Date(`${log.recordedDate}T00:00:00`);
      return {
        placeId: log.placeId!,
        name: log.placeName,
        date: log.recordedDate,
        period: hour < 12 ? '오전' : '오후',
        day: Math.max(1, Math.round((visit.getTime() - start.getTime()) / 86400000) + 1),
      };
    });
}

export function NewMomentStepTwoScreen() {
  const router = useRouter();
  // 새 기록에는 활성 프로필만 선택할 수 있다.
  const { data: pets = [] } = usePets();
  // 여행 목록의 반려동물 이름은 지워진 프로필까지 조회해 최신 이름으로 그린다.
  const { data: allPets = [] } = useAllPets();
  const petsById = useMemo(() => toPetsById(allPets), [allPets]);
  const draft = useLogDraftStore((state) => state.draft);
  const updateDraft = useLogDraftStore((state) => state.updateDraft);
  const petSheetRef = useRef<MomentPetSelectionSheetHandle>(null);
  const [selectedPetIds, setSelectedPetIds] = useState<string[]>(draft.petIds);
  const [selectedTripId, setSelectedTripId] = useState<string | undefined>(draft.tripId);
  const [selectedPlace, setSelectedPlace] = useState<CoursePlace | undefined>(() =>
    draft.placeId && draft.placeName && draft.recordedDate
      ? { placeId: draft.placeId, name: draft.placeName, date: draft.recordedDate, period: '오후', day: 1 }
      : undefined,
  );
  const [searchVisible, setSearchVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const recentTrips = useMemo(() => {
    const cutoff = minusOneMonth(TODAY);
    return [...mockTrips]
      .filter((trip) => trip.endDate >= cutoff && trip.startDate <= TODAY)
      .sort((a, b) => {
        const aActive = a.startDate <= TODAY && a.endDate >= TODAY;
        const bActive = b.startDate <= TODAY && b.endDate >= TODAY;
        if (aActive !== bActive) return aActive ? -1 : 1;
        return b.startDate.localeCompare(a.startDate);
      })
      .slice(0, 5);
  }, []);
  const selectedTrip = recentTrips.find((trip) => trip.tripId === selectedTripId);
  const coursePlaces = selectedTrip ? placesForTrip(selectedTrip) : [];
  const previewUri = draft.localPhotoUri ?? undefined;
  const filteredDirectPlaces = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query) return DIRECT_PLACES;

    // TODO: 장소 검색 API 연결 시 이 필터를 검색 서비스 호출 결과로 교체한다.
    return DIRECT_PLACES.filter((place) => place.name.toLocaleLowerCase().includes(query));
  }, [searchQuery]);

  const selectTrip = (trip: Trip) => {
    setSelectedTripId(trip.tripId);
    setSelectedPlace(undefined);
    // 여행 스냅샷에 지워진 반려동물이 섞여 있을 수 있어 활성 프로필만 남긴다.
    const tripPetIds = trip.companions
      .map((companion) => companion.petId)
      .filter((petId) => pets.some((pet) => pet.petId === petId));
    const nextPetIds = tripPetIds.length > 0 ? tripPetIds : pets[0] ? [pets[0].petId] : [];
    setSelectedPetIds(nextPetIds);
    updateDraft({ tripId: trip.tripId, placeId: undefined, placeName: null, recordedDate: null, petIds: nextPetIds });
  };
  const selectPlace = (place: CoursePlace) => {
    setSelectedPlace(place);
    updateDraft({ placeId: place.placeId, placeName: place.name, recordedDate: place.date });
  };
  const applyPets = (petIds: string[]) => {
    setSelectedPetIds(petIds);
    updateDraft({ petIds });
  };
  const removePet = (petId: string) => applyPets(selectedPetIds.filter((id) => id !== petId));
  const selectedPets = pets.filter((pet) => selectedPetIds.includes(pet.petId));
  const canContinue = Boolean(draft.localPhotoUri && selectedPlace && selectedPetIds.length > 0);
  const openPlaceSearch = () => {
    setSearchQuery('');
    setSearchVisible(true);
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <MomentStepHeader onBack={() => router.back()} step={2} title="언제, 어디에서 함께했나요?" />

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.photoCard}>
          <RemoteImage borderRadius={radius.md} style={styles.preview} uri={previewUri} />
          <View style={styles.photoInfo}>
            <Pressable onPress={() => router.back()} style={styles.outlineSmallButton}>
              <Text style={styles.outlineSmallLabel}>사진 변경</Text>
            </Pressable>
            <Text style={styles.fieldLabel}>함께한 반려동물</Text>
            {pets.length === 0 ? (
              <Text style={styles.emptyText}>등록된 반려동물이 없어요. 프로필에서 먼저 등록해 주세요.</Text>
            ) : (
              <View style={styles.petChips}>
                {selectedPets.map((pet) => (
                  <View key={pet.petId} style={styles.petChip}>
                    <Avatar fallbackIcon="paw" size={28} uri={pet.profileImage} />
                    <Text style={styles.petChipName}>{pet.name}</Text>
                    <Pressable
                      accessibilityLabel={`${pet.name} 선택 해제`}
                      hitSlop={8}
                      onPress={() => removePet(pet.petId)}
                    >
                      <Ionicons color={colors.iconGray} name="close" size={17} />
                    </Pressable>
                  </View>
                ))}
                <Pressable onPress={() => petSheetRef.current?.open()} style={styles.addPetButton}>
                  <Text style={styles.addPetLabel}>＋ 추가</Text>
                </Pressable>
              </View>
            )}
          </View>
        </View>

        <View style={styles.sectionHeading}>
          <Text style={styles.sectionTitle}>내 여행 코스에서 선택</Text>
          <Text style={styles.sectionSubtitle}>최근 한 달의 여행 코스를 불러왔어요</Text>
        </View>
        {recentTrips.length === 0 ? (
          <View style={styles.emptyCard}><Text style={styles.emptyText}>최근 한 달 이내의 여행 코스가 없어요.</Text></View>
        ) : recentTrips.map((trip) => {
          const selected = trip.tripId === selectedTripId;
          const petNames = resolveCompanions(trip.companions, petsById).map((companion) => companion.name);
          return (
            <Pressable key={trip.tripId} onPress={() => selectTrip(trip)} style={[styles.optionCard, selected && styles.selectedCard]}>
              <Ionicons color={selected ? colors.primary : colors.iconGray} name={selected ? 'checkmark-circle' : 'ellipse-outline'} size={24} />
              <View style={styles.optionInfo}>
                <Text style={styles.optionTitle}>{trip.title}</Text>
                <Text style={styles.optionMeta}>{formatRange(trip)}</Text>
                <Text style={styles.optionMeta}>{petNames.join(' · ') || '반려동물 없음'} · {trip.logCount}개 장소</Text>
              </View>
              <Ionicons color={colors.textPrimary} name="chevron-forward" size={20} />
            </Pressable>
          );
        })}

        {selectedTrip ? (
          <View style={styles.placesSection}>
            <Text style={styles.fieldLabel}>이 코스의 방문 장소</Text>
            {coursePlaces.map((place) => {
              const selected = selectedPlace?.placeId === place.placeId;
              return (
                <Pressable key={place.placeId} onPress={() => selectPlace(place)} style={[styles.placeRow, selected && styles.selectedCard]}>
                  <Ionicons color={selected ? colors.primary : colors.iconGray} name={selected ? 'checkmark-circle' : 'ellipse-outline'} size={22} />
                  <Ionicons color={colors.textPrimary} name="location-outline" size={20} />
                  <Text style={styles.placeName}>{place.name}</Text>
                  <Text style={styles.placeMeta}>Day {place.day} · {place.period}</Text>
                </Pressable>
              );
            })}
          </View>
        ) : null}

        <Pressable onPress={openPlaceSearch} style={styles.searchButton}>
          <Ionicons color={colors.secondary} name="search-outline" size={20} />
          <Text style={styles.searchLabel}>다른 장소 직접 검색</Text>
        </Pressable>
        {selectedPlace ? (
          <View style={styles.selectionSummary}>
            <Ionicons color={colors.secondary} name="location" size={18} />
            <Text style={styles.summaryText}>{selectedPlace.name} · 방문 날짜 {selectedPlace.date}</Text>
          </View>
        ) : null}
      </ScrollView>

      <View style={styles.footer}>
        <Pressable
          accessibilityState={{ disabled: !canContinue }}
          disabled={!canContinue}
          onPress={() => router.push('/travel-logs/new-moment/style')}
          style={[styles.nextButton, !canContinue && styles.nextButtonDisabled]}
        >
          <Text style={[styles.nextLabel, !canContinue && styles.nextLabelDisabled]}>다음</Text>
        </Pressable>
      </View>

      <MomentPetSelectionSheet onApply={applyPets} pets={pets} ref={petSheetRef} value={selectedPetIds} />
      <Modal animationType="slide" onRequestClose={() => setSearchVisible(false)} transparent visible={searchVisible}>
        <View style={styles.modalOverlay}>
          <Pressable
            accessibilityLabel="장소 검색 닫기"
            onPress={() => setSearchVisible(false)}
            style={styles.modalBackdrop}
          />
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
            pointerEvents="box-none"
            style={styles.modalKeyboard}
          >
            <View style={styles.searchSheet}>
              <View style={styles.modalHandle} />
              <Text style={styles.modalTitle}>장소 직접 검색</Text>
              <Text style={styles.sectionSubtitle}>등록할 장소를 검색해 주세요</Text>
              <View style={styles.searchInputWrapper}>
                <Ionicons color={colors.iconGray} name="search-outline" size={20} />
                <TextInput
                  autoFocus
                  onChangeText={setSearchQuery}
                  placeholder="장소명 검색"
                  placeholderTextColor={colors.textSecondary}
                  returnKeyType="search"
                  style={styles.searchInput}
                  value={searchQuery}
                />
                {searchQuery ? (
                  <Pressable
                    accessibilityLabel="검색어 지우기"
                    hitSlop={8}
                    onPress={() => setSearchQuery('')}
                  >
                    <Ionicons color={colors.iconGray} name="close-circle" size={20} />
                  </Pressable>
                ) : null}
              </View>
              <ScrollView keyboardShouldPersistTaps="handled" style={styles.searchResults}>
                {filteredDirectPlaces.length > 0 ? (
                  filteredDirectPlaces.map((place) => (
                    <Pressable
                      key={place.placeId}
                      onPress={() => {
                        setSelectedTripId(undefined);
                        updateDraft({ tripId: undefined });
                        selectPlace(place);
                        setSearchVisible(false);
                      }}
                      style={styles.directPlaceRow}
                    >
                      <Ionicons color={colors.secondary} name="location-outline" size={23} />
                      <Text style={styles.placeName}>{place.name}</Text>
                      <Ionicons color={colors.iconGray} name="chevron-forward" size={19} />
                    </Pressable>
                  ))
                ) : (
                  <View style={styles.noSearchResult}>
                    <Ionicons color={colors.iconGray} name="search-outline" size={28} />
                    <Text style={styles.emptyText}>검색 결과가 없어요</Text>
                  </View>
                )}
              </ScrollView>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  addPetButton: { alignItems: 'center', borderColor: colors.secondary, borderRadius: radius.sm, borderWidth: 1, justifyContent: 'center', paddingHorizontal: spacing.sm },
  addPetLabel: { color: colors.secondary, fontSize: 14, fontWeight: '600' },
  content: { gap: spacing.sm, paddingBottom: spacing.md, paddingHorizontal: spacing.md },
  directPlaceRow: { alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: spacing.sm, paddingVertical: spacing.md },
  emptyCard: { borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, padding: spacing.md },
  emptyText: { color: colors.textSecondary, fontSize: 13, lineHeight: 18 },
  fieldLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
  footer: { borderTopColor: colors.border, borderTopWidth: 1, padding: spacing.md },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  headerTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '700' },
  iconButton: { padding: spacing.sm },
  iconPlaceholder: { width: 40 },
  modalBackdrop: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  modalHandle: { alignSelf: 'center', backgroundColor: colors.border, borderRadius: 2, height: 4, width: 42 },
  modalKeyboard: { flex: 1, justifyContent: 'flex-end', pointerEvents: 'box-none' },
  modalOverlay: { backgroundColor: overlayColors.scrim, flex: 1 },
  modalTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: spacing.sm, textAlign: 'center' },
  noSearchResult: { alignItems: 'center', gap: spacing.sm, justifyContent: 'center', minHeight: 150 },
  nextButton: { alignItems: 'center', backgroundColor: colors.primary, borderRadius: radius.sm, paddingVertical: 14 },
  nextButtonDisabled: { backgroundColor: colors.neutralGray },
  nextLabel: { color: colors.surface, fontSize: typography.body.fontSize, fontWeight: '700' },
  nextLabelDisabled: { color: colors.textSecondary },
  optionCard: { alignItems: 'center', backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, flexDirection: 'row', gap: spacing.sm, padding: spacing.sm },
  optionInfo: { flex: 1 },
  optionMeta: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  optionTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '700' },
  outlineSmallButton: { alignSelf: 'flex-start', borderColor: colors.secondary, borderRadius: radius.sm, borderWidth: 1, paddingHorizontal: spacing.sm, paddingVertical: 6 },
  outlineSmallLabel: { color: colors.secondary, fontSize: 13, fontWeight: '600' },
  petChip: { alignItems: 'center', borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, flexDirection: 'row', gap: 6, paddingRight: spacing.sm },
  petChipName: { color: colors.textPrimary, fontSize: 13, fontWeight: '600' },
  petChips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  photoCard: { borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, flexDirection: 'row', gap: spacing.md, padding: spacing.sm },
  photoInfo: { flex: 1, gap: spacing.sm },
  placeMeta: { color: colors.textSecondary, fontSize: 12 },
  placeName: { color: colors.textPrimary, flex: 1, fontSize: 14, fontWeight: '600' },
  placeRow: { alignItems: 'center', borderColor: colors.border, borderRadius: radius.sm, borderWidth: 1, flexDirection: 'row', gap: spacing.sm, padding: spacing.sm },
  placesSection: { gap: 6, marginTop: spacing.xs },
  preview: { height: 118, width: 118 },
  progressDot: { backgroundColor: colors.surface, borderColor: colors.primary, borderRadius: 8, borderWidth: 2, height: 16, position: 'absolute', right: -8, top: -6, width: 16 },
  progressEnd: { borderColor: colors.border, borderRadius: 8, borderWidth: 2, height: 16, width: 16 },
  progressFill: { backgroundColor: colors.primary, height: 2, width: '55%' },
  progressLabel: { color: colors.textPrimary, fontSize: 15 },
  progressRow: { alignItems: 'center', flexDirection: 'row', gap: spacing.md, paddingBottom: spacing.md, paddingHorizontal: spacing.xl },
  progressTrack: { backgroundColor: colors.border, flex: 1, height: 2, position: 'relative' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  searchButton: { alignItems: 'center', borderColor: colors.secondary, borderRadius: radius.sm, borderWidth: 1, flexDirection: 'row', gap: spacing.sm, justifyContent: 'center', marginTop: spacing.xs, paddingVertical: spacing.sm },
  searchLabel: { color: colors.secondary, fontSize: 14, fontWeight: '600' },
  searchInput: { color: colors.textPrimary, flex: 1, fontSize: 15, paddingVertical: 0 },
  searchInputWrapper: { alignItems: 'center', backgroundColor: colors.neutralGray, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, flexDirection: 'row', gap: spacing.sm, minHeight: 48, paddingHorizontal: spacing.md },
  searchResults: { marginTop: spacing.xs, maxHeight: 300 },
  searchSheet: { backgroundColor: colors.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, gap: spacing.sm, minHeight: 410, padding: spacing.lg, paddingBottom: spacing.xl },
  sectionHeading: { gap: 2, marginTop: spacing.sm },
  sectionSubtitle: { color: colors.textSecondary, fontSize: 12 },
  sectionTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '700' },
  selectedCard: { backgroundColor: colors.primarySoft, borderColor: colors.primary },
  selectionSummary: { alignItems: 'center', backgroundColor: colors.seaSoftLight, borderRadius: radius.sm, flexDirection: 'row', gap: spacing.sm, padding: spacing.sm },
  summaryText: { color: colors.textPrimary, fontSize: 13 },
});

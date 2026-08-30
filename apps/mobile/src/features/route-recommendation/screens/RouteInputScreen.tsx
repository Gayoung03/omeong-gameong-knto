import Ionicons from '@expo/vector-icons/Ionicons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { isAxiosError } from 'axios';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  Image,
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

import { CalendarRangePicker } from '../components/InlineDateTimePicker';
import {
  isPriorityPreset,
  isUserCriterion,
  PRIORITY_PRESETS,
  toPersonalizationPayload,
  USER_CRITERIA_OPTIONS,
  type PriorityMode,
  type PriorityPreset,
  type UserCriterion,
} from '../personalization';
import { formatTripDuration } from '../utils/tripDuration';
import { savePendingRoute } from '../services/pendingRoute';

import { ConfirmModal } from '@/src/components/feedback/ConfirmModal';
import { brandAssets } from '@/src/config/brandAssets';
import { getAuthSession } from '@/src/features/auth/services/authStorage';
import { searchAccommodations } from '@/src/features/places/api/placesApi';
import type { Place } from '@/src/features/places/types/place';
import { usePets } from '@/src/features/profile/hooks/usePets';
import { createRouteRecommendation } from '@/src/features/trips/api/tripsApi';
import type { ServerTransportType, ServerTripPace } from '@/src/features/trips/types/routeApi';
import { colors as theme, overlayColors, radius, spacing, typography } from '@/src/theme';

const LEGACY_DRAFT_KEY = 'route-input-draft';
const DRAFT_KEY_PREFIX = 'route-input-draft:';

function routeDraftKey(userId: string): string {
  return `${DRAFT_KEY_PREFIX}${userId}`;
}

/**
 * 색상 별칭. 값은 모두 theme 토큰을 가리킨다.
 * 색상(#23)과 글자 크기·여백을 차례로 토큰으로 맞췄으므로, 남은 것은 이름뿐이다.
 * TODO: 별칭을 걷어내고 `theme.*` 을 직접 참조하도록 정리한다.
 */
const colors = {
  orange: theme.primary,
  mint: theme.sea,
  deepMint: theme.seaDeep,
  ink: theme.textPrimary,
  gray: theme.textSecondary,
  lightGray: theme.neutralGray,
  line: theme.divider,
  white: theme.surface,
  cream: theme.primarySoft,
  red: theme.error,
};

type Trip = { title: string; startAt: string; endAt: string };
type Stay = { id: string; placeId?: string; name: string; period: string; address: string };
type EditTarget = 'stay' | null;
type TripPhase = 'dates' | 'details';
type FirstDayStart = 'stay' | 'other' | null;

type RouteDraft = {
  trip: Trip;
  transportOptions: string[];
  transport: string;
  stays: Stay[];
  firstDayStart: FirstDayStart;
  selectedPetIds: string[];
  departureLocation: string;
  places: string[];
  pace: string;
  priorityMode: PriorityMode;
  priorityPreset: PriorityPreset;
  userCriteria: UserCriterion[];
};

const PLACE_TYPE_OPTIONS = [
  '바다·해변',
  '카페',
  '산책·공원',
  '실내 관광',
  '오름·자연',
  '체험',
  '맛집',
  '문화·전시',
] as const;

const LEGACY_PLACE_TYPE_MAP: Record<string, (typeof PLACE_TYPE_OPTIONS)[number]> = {
  바다: '바다·해변',
  카페: '카페',
  산책로: '산책·공원',
  '실내 관광지': '실내 관광',
  오름: '오름·자연',
};

const SUPPORTED_TRANSPORT_OPTIONS = ['렌터카', '자가용', '택시', '도보'];

type StoredRouteDraft = {
  version: 6;
  draft: RouteDraft;
  currentStep: number;
};

const initialDraft: RouteDraft = {
  trip: {
    title: '',
    startAt: '',
    endAt: '',
  },
  transportOptions: ['렌터카', '자가용', '택시', '도보'],
  transport: '',
  stays: [],
  firstDayStart: null,
  selectedPetIds: [],
  departureLocation: '',
  places: [],
  pace: '여유롭게',
  priorityMode: 'manual',
  priorityPreset: 'balanced',
  userCriteria: [],
};

/**
 * 입력 단계 순서.
 * `optional` 은 `requestRecommendation` 의 검증에서 빠져 있는 항목이다 — 건너뛸 수 있다.
 */
const STEPS = [
  { key: 'trip', optional: false },
  { key: 'transport', optional: false },
  { key: 'stay', optional: true },
  { key: 'pet', optional: false },
  { key: 'places', optional: false },
  { key: 'pace', optional: true },
  { key: 'priority', optional: true },
] as const;

const REVIEW_STEP = STEPS.length;

const formatShortDate = (iso: string) => {
  const date = new Date(iso);
  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
};

const getStayNightOptions = (trip: Trip) => {
  const start = new Date(trip.startAt);
  const end = new Date(trip.endAt);
  const options: { value: string; label: string; dateLabel: string }[] = [];
  const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const lastDate = new Date(end.getFullYear(), end.getMonth(), end.getDate());

  while (cursor < lastDate) {
    const nextDate = new Date(cursor);
    nextDate.setDate(nextDate.getDate() + 1);
    const night = options.length + 1;
    options.push({
      value: `${night}일차`,
      label: `${night}박`,
      dateLabel: `${cursor.getMonth() + 1}/${cursor.getDate()} → ${nextDate.getMonth() + 1}/${nextDate.getDate()}`,
    });
    cursor.setDate(cursor.getDate() + 1);
  }

  return options;
};

const parseStayPeriods = (period: string) => {
  const matchedDays = period.match(/\d+/g)?.map(Number) ?? [];
  if (matchedDays.length === 2 && period.includes('~')) {
    return Array.from(
      { length: matchedDays[1] - matchedDays[0] + 1 },
      (_, index) => `${matchedDays[0] + index}일차`,
    );
  }
  return matchedDays.map((day) => `${day}일차`);
};

const formatStayPeriods = (periods: string[]) => {
  const days = periods
    .map((period) => Number(period.replace(/\D/g, '')))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (days.length === 0) return '';
  if (days.length === 1) return `${days[0]}일차`;
  const isContinuous = days.every((day, index) => index === 0 || day === days[index - 1] + 1);
  return isContinuous
    ? `${days[0]}~${days.at(-1)}일차`
    : days.map((day) => `${day}일차`).join(', ');
};

const toStayRequest = (stay: Stay, trip: Trip) => {
  const days = parseStayPeriods(stay.period)
    .map((period) => Number(period.replace(/\D/g, '')))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);
  const checkInAt = new Date(trip.startAt);
  checkInAt.setDate(checkInAt.getDate() + Math.max((days[0] ?? 1) - 1, 0));
  checkInAt.setHours(15, 0, 0, 0);
  const checkOutAt = new Date(trip.startAt);
  checkOutAt.setDate(checkOutAt.getDate() + (days.at(-1) ?? 1));
  checkOutAt.setHours(11, 0, 0, 0);
  return {
    placeId: stay.placeId,
    name: stay.name,
    address: stay.address || stay.name,
    checkInAt: checkInAt.toISOString(),
    checkOutAt: checkOutAt.toISOString(),
  };
};

function ChoiceChip({
  label,
  selected,
  onPress,
  onDelete,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  onDelete?: () => void;
}) {
  return (
    <View style={[styles.choiceChip, selected && styles.choiceChipSelected]}>
      <Pressable accessibilityState={{ selected }} onPress={onPress}>
        <Text style={[styles.choiceChipText, selected && styles.choiceChipTextSelected]}>
          {label}
        </Text>
      </Pressable>
      {onDelete ? (
        <Pressable accessibilityLabel={`${label} 삭제`} hitSlop={8} onPress={onDelete}>
          <Ionicons color={selected ? colors.white : colors.gray} name="close-circle" size={14} />
        </Pressable>
      ) : null}
    </View>
  );
}

function QuestionStep({
  icon,
  title,
  description,
  children,
  onEdit,
  actionLabel = '수정',
  accent = colors.orange,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  children: React.ReactNode;
  onEdit?: () => void;
  actionLabel?: string;
  accent?: string;
}) {
  return (
    <View style={styles.questionStep}>
      <View style={[styles.questionIcon, { backgroundColor: `${accent}16` }]}>
        <Ionicons color={accent} name={icon} size={24} />
      </View>
      <View style={styles.questionHeading}>
        <View style={styles.questionCopy}>
          <Text style={styles.questionTitle}>{title}</Text>
          <Text style={styles.questionDescription}>{description}</Text>
        </View>
        {onEdit ? (
          <Pressable onPress={onEdit} style={styles.editButton}>
            <Ionicons color={colors.gray} name="pencil-outline" size={13} />
            <Text style={styles.editText}>{actionLabel}</Text>
          </Pressable>
        ) : null}
      </View>
      {children}
    </View>
  );
}

function serializeDraft(draft: RouteDraft, currentStep: number): string {
  const stored: StoredRouteDraft = { version: 6, draft, currentStep };
  return JSON.stringify(stored);
}

function restoreDraft(saved: string): { draft: RouteDraft; currentStep: number } {
  const parsed = JSON.parse(saved) as Partial<RouteDraft> | Partial<StoredRouteDraft>;
  const savedDraft: Partial<RouteDraft> =
    'draft' in parsed && parsed.draft
      ? (parsed.draft as Partial<RouteDraft>)
      : (parsed as Partial<RouteDraft>);
  const storedVersion =
    'version' in parsed && typeof parsed.version === 'number' ? parsed.version : 0;
  if (storedVersion < 5) {
    return { draft: initialDraft, currentStep: 0 };
  }
  const savedTrip = savedDraft.trip as Trip | undefined;
  const priorityPreset = isPriorityPreset(savedDraft.priorityPreset)
    ? savedDraft.priorityPreset
    : initialDraft.priorityPreset;
  const userCriteria = Array.isArray(savedDraft.userCriteria)
    ? savedDraft.userCriteria.filter(isUserCriterion)
    : initialDraft.userCriteria;
  const priorityMode: PriorityMode =
    savedDraft.priorityMode === 'manual' || savedDraft.priorityMode === 'preset'
      ? savedDraft.priorityMode
      : userCriteria.length > 0
        ? 'manual'
        : 'preset';
  const places = Array.isArray(savedDraft.places)
    ? [
        ...new Set(
          savedDraft.places
            .map((place) => LEGACY_PLACE_TYPE_MAP[place] ?? place)
            .filter((place) => PLACE_TYPE_OPTIONS.some((option) => option === place)),
        ),
      ].slice(0, 3)
    : initialDraft.places;
  const stays = Array.isArray(savedDraft.stays) ? savedDraft.stays : initialDraft.stays;
  const firstDayStart: FirstDayStart =
    savedDraft.firstDayStart === 'stay' || savedDraft.firstDayStart === 'other'
      ? savedDraft.firstDayStart
      : null;
  const requestedStep = 'currentStep' in parsed ? parsed.currentStep : REVIEW_STEP;
  const currentStep =
    typeof requestedStep === 'number'
      ? Math.max(0, Math.min(REVIEW_STEP, requestedStep))
      : REVIEW_STEP;

  return {
    draft: {
      ...initialDraft,
      ...savedDraft,
      stays,
      firstDayStart,
      transportOptions: SUPPORTED_TRANSPORT_OPTIONS,
      transport: SUPPORTED_TRANSPORT_OPTIONS.includes(savedDraft.transport ?? '')
        ? savedDraft.transport!
        : '',
      places,
      priorityMode,
      priorityPreset: priorityMode === 'manual' ? 'balanced' : priorityPreset,
      userCriteria: priorityMode === 'manual' ? userCriteria.slice(0, 3) : [],
      trip: savedTrip?.startAt && savedTrip?.endAt ? savedTrip : initialDraft.trip,
    },
    currentStep,
  };
}

function validateStep(index: number, draft: RouteDraft): string | null {
  if (
    index === 0 &&
    (!draft.trip.title || new Date(draft.trip.endAt) <= new Date(draft.trip.startAt))
  ) {
    return '여행 일정을 다시 확인해주세요.';
  }
  if (index === 1 && !draft.transport) return '이동수단을 하나 선택해주세요.';
  if (
    index === 2 &&
    (draft.stays.length === 0 || draft.firstDayStart === 'other') &&
    !draft.departureLocation.trim()
  ) {
    return '첫날 여행을 시작할 장소를 골라주세요.';
  }
  if (index === 2 && draft.stays.length > 0 && draft.firstDayStart === null) {
    return '첫날 숙소에서 출발할지 다른 장소에서 출발할지 골라주세요.';
  }
  if (index === 3 && draft.selectedPetIds.length === 0) {
    return '함께 여행할 반려동물을 한 마리 이상 골라주세요.';
  }
  if (index === 4 && draft.places.length === 0) {
    return '가고 싶은 장소 유형을 한 개 이상 선택해주세요.';
  }
  if (index === 6 && draft.priorityMode === 'manual' && draft.userCriteria.length === 0) {
    return '중요한 기준을 하나 이상 고르거나 건너뛰어주세요.';
  }
  return null;
}

export function RouteInputScreen() {
  const router = useRouter();
  const { data: pets = [], isPending: isPetsPending } = usePets();
  const [draft, setDraft] = useState<RouteDraft>(initialDraft);
  const [draftStorageKey, setDraftStorageKey] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<EditTarget>(null);
  const [tripPhase, setTripPhase] = useState<TripPhase>('dates');
  const [editingStayId, setEditingStayId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [staySearchQuery, setStaySearchQuery] = useState('');
  const [staySearchResults, setStaySearchResults] = useState<Place[]>([]);
  const [staySearchLoading, setStaySearchLoading] = useState(false);
  const [staySearchError, setStaySearchError] = useState('');
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [autoSaveError, setAutoSaveError] = useState('');
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /**
   * 삭제를 기다리는 숙소.
   *
   * 예전에는 `Alert.alert` 으로 물었는데 **웹에서는 뜨지 않아 삭제가 아예 안 됐다.**
   * 확인을 받아야 하는 동작은 `ConfirmModal` 을 쓴다.
   */
  const [pendingStayDelete, setPendingStayDelete] = useState<Stay | null>(null);
  const [formError, setFormError] = useState('');
  const [pageError, setPageError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  /** 현재 표시하는 단계. STEPS.length 면 최종 확인 화면이다. */
  const [openIndex, setOpenIndex] = useState(0);
  const [returnToReview, setReturnToReview] = useState(false);

  const isReviewStep = openIndex === REVIEW_STEP;

  const goNextStep = (index: number) => {
    if (index === 0 && tripPhase === 'dates') {
      if (!draft.trip.startAt || !draft.trip.endAt) {
        setPageError('도착일과 출발일을 모두 골라주세요.');
        return;
      }
      setPageError('');
      setTripPhase('details');
      return;
    }
    const error = validateStep(index, draft);
    if (error) {
      setPageError(error);
      return;
    }
    setPageError('');
    setOpenIndex(returnToReview ? REVIEW_STEP : Math.min(REVIEW_STEP, index + 1));
    setReturnToReview(false);
  };

  const nextStepLabel = (index: number) => {
    if (index === 0 && tripPhase === 'dates') return '시간 선택';
    return index === STEPS.length - 1 ? '확인' : '다음';
  };

  const skipCurrentStep = () => {
    if (openIndex === 2) {
      updateDraft('stays', []);
      updateDraft('firstDayStart', null);
      if (!draft.departureLocation) updateDraft('departureLocation', '제주국제공항');
    }
    if (openIndex === 5) updateDraft('pace', initialDraft.pace);
    if (openIndex === 6) {
      setDraft((current) => ({
        ...current,
        priorityMode: 'manual',
        priorityPreset: 'balanced',
        userCriteria: [],
      }));
    }
    setPageError('');
    setOpenIndex(returnToReview ? REVIEW_STEP : Math.min(REVIEW_STEP, openIndex + 1));
    setReturnToReview(false);
  };
  const stayNightOptions = getStayNightOptions(draft.trip);

  useEffect(() => {
    void (async () => {
      try {
        const session = await getAuthSession();
        // 업데이트 전에 저장된 로컬 계정 세션에는 userId가 없으므로 이메일을 한 번
        // 대신 사용한다. 새로 로그인하면 항상 서버 userId가 저장된다.
        const accountKey = session?.userId || session?.email;
        if (!accountKey) {
          setPageError('로그인 정보를 확인하지 못했어요. 다시 로그인해주세요.');
          return;
        }

        const storageKey = routeDraftKey(accountKey);
        setDraftStorageKey(storageKey);

        // 예전 공용 키는 계정 사이에 입력 정보가 섞일 수 있으므로 복원하지 않는다.
        await AsyncStorage.removeItem(LEGACY_DRAFT_KEY);
        const saved = await AsyncStorage.getItem(storageKey);
        if (saved) {
          const restored = restoreDraft(saved);
          setDraft(restored.draft);
          setOpenIndex(restored.currentStep);
        }
      } catch {
        setPageError('저장한 입력 정보를 불러오지 못했어요. 새로 입력해주세요.');
      } finally {
        setHydrated(true);
      }
    })();
  }, []);

  useEffect(() => {
    if (!hydrated || !draftStorageKey) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      void AsyncStorage.setItem(draftStorageKey, serializeDraft(draft, openIndex))
        .then(() => setAutoSaveError(''))
        .catch(() => setAutoSaveError('입력 내용을 자동 저장하지 못했어요.'));
    }, 350);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [draft, draftStorageKey, hydrated, openIndex]);

  /** 접힌 카드에 한 줄로 보여줄 내용 */
  const stepSummaries = [
    `${draft.trip.title} · ${formatTripDuration(draft.trip.startAt, draft.trip.endAt)}`,
    draft.transport || '미선택',
    draft.stays.length === 0
      ? '건너뜀'
      : draft.stays.length === 1
        ? draft.stays[0].name
        : `${draft.stays[0].name} 외 ${draft.stays.length - 1}곳`,
    pets
      .filter((pet) => draft.selectedPetIds.includes(pet.petId))
      .map((pet) => pet.name)
      .join(', ') || '미선택',
    draft.places.join(', ') || '미선택',
    draft.pace,
    draft.priorityMode === 'manual'
      ? draft.userCriteria.length > 0
        ? draft.userCriteria
            .map(
              (criterion) =>
                USER_CRITERIA_OPTIONS.find((option) => option.value === criterion)?.label,
            )
            .filter(Boolean)
            .join(', ')
        : '골고루 추천'
      : (PRIORITY_PRESETS.find((preset) => preset.value === draft.priorityPreset)?.label ??
        '골고루 추천'),
  ];

  const updateDraft = <K extends keyof RouteDraft>(key: K, value: RouteDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setPageError('');
  };

  const loadStayOptions = async (query = '') => {
    setStaySearchLoading(true);
    setStaySearchError('');
    try {
      setStaySearchResults(await searchAccommodations(query));
    } catch {
      setStaySearchResults([]);
      setStaySearchError('숙소 목록을 불러오지 못했어요. 직접 입력하거나 다시 시도해주세요.');
    } finally {
      setStaySearchLoading(false);
    }
  };

  const openStayEditor = (stay?: Stay) => {
    setFormError('');
    setEditingStayId(stay?.id ?? null);
    setFormValues(stay ?? { id: '', placeId: '', name: '', period: '', address: '' });
    setStaySearchQuery(stay?.name ?? '');
    setStaySearchResults([]);
    setStaySearchError('');
    setEditTarget('stay');
    void loadStayOptions(stay?.name ?? '');
  };

  const toggleStayPeriod = (period: string) => {
    const selectedPeriods = parseStayPeriods(formValues.period ?? '');
    const nextPeriods = selectedPeriods.includes(period)
      ? selectedPeriods.filter((selected) => selected !== period)
      : [...selectedPeriods, period];
    setFormValues((values) => ({ ...values, period: formatStayPeriods(nextPeriods) }));
    setFormError('');
  };

  const updateTripTime = (field: 'startAt' | 'endAt', hour: number, minute: number) => {
    const current = new Date(draft.trip[field]);
    current.setHours(hour, minute, 0, 0);
    updateDraft('trip', { ...draft.trip, [field]: current.toISOString() });
  };

  const updateTripDates = (start: Date, end: Date | null) => {
    const nextStart = new Date(start);
    nextStart.setHours(10, 0, 0, 0);
    const nextEnd = end ? new Date(end) : null;
    nextEnd?.setHours(18, 0, 0, 0);
    setDraft((current) => ({
      ...current,
      stays: [],
      trip: {
        ...current.trip,
        startAt: nextStart.toISOString(),
        endAt: nextEnd?.toISOString() ?? '',
      },
    }));
    setPageError('');
  };

  const closeEditor = () => {
    setEditTarget(null);
    setEditingStayId(null);
    setFormValues({});
    setFormError('');
    setStaySearchQuery('');
    setStaySearchResults([]);
    setStaySearchError('');
  };

  const saveEditor = () => {
    if (editTarget === 'stay') {
      if (!formValues.name || !formValues.period) {
        setFormError('숙소 이름과 숙박 일차를 입력해주세요.');
        return;
      }
      const selectedPeriods = parseStayPeriods(formValues.period);
      const occupiedPeriods = new Set(
        draft.stays
          .filter((stay) => stay.id !== editingStayId)
          .flatMap((stay) => parseStayPeriods(stay.period)),
      );
      const duplicatedPeriod = selectedPeriods.find((period) => occupiedPeriods.has(period));
      if (duplicatedPeriod) {
        setFormError(`${duplicatedPeriod}에는 이미 다른 숙소가 지정되어 있어요.`);
        return;
      }
      const nextStay: Stay = {
        id:
          editingStayId ??
          `stay-${formValues.period.replace(/\s+/g, '-')}-${formValues.name.replace(/\s+/g, '-')}`,
        name: formValues.name,
        placeId: formValues.placeId || undefined,
        period: formValues.period,
        address: formValues.address,
      };
      updateDraft(
        'stays',
        editingStayId
          ? draft.stays.map((stay) => (stay.id === editingStayId ? nextStay : stay))
          : [...draft.stays, nextStay],
      );
    }

    closeEditor();
  };

  const togglePlaceType = (place: string) => {
    if (draft.places.includes(place)) {
      updateDraft(
        'places',
        draft.places.filter((selectedPlace) => selectedPlace !== place),
      );
      return;
    }
    if (draft.places.length >= 3) {
      setPageError('가고 싶은 장소 유형은 최대 3개까지 선택할 수 있어요.');
      return;
    }
    updateDraft('places', [...draft.places, place]);
  };

  const switchPriorityMode = (mode: PriorityMode) => {
    setDraft((current) => ({
      ...current,
      priorityMode: mode,
      priorityPreset: 'balanced',
      userCriteria: [],
    }));
    setPageError('');
  };

  const toggleUserCriterion = (criterion: UserCriterion) => {
    if (draft.userCriteria.includes(criterion)) {
      updateDraft(
        'userCriteria',
        draft.userCriteria.filter((item) => item !== criterion),
      );
      return;
    }
    if (draft.userCriteria.length >= 3) {
      setPageError('중요한 기준은 최대 3개까지 선택할 수 있어요.');
      return;
    }
    updateDraft('userCriteria', [...draft.userCriteria, criterion]);
  };

  const closeFlow = async () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    try {
      if (draftStorageKey) {
        await AsyncStorage.setItem(draftStorageKey, serializeDraft(draft, openIndex));
      }
    } catch {
      setAutoSaveError('입력 내용을 저장하지 못했어요.');
    }
    router.back();
  };

  /**
   * 입력을 처음 상태로 되돌린다.
   *
   * 임시 저장본까지 지운다. 화면만 비우면 다시 들어왔을 때 지운 내용이 되살아나
   * "초기화한 게 맞나" 싶어지기 때문이다.
   */
  const resetAll = async () => {
    setResetConfirmOpen(false);
    setDraft(initialDraft);
    setOpenIndex(0);
    setTripPhase('dates');
    setReturnToReview(false);
    setPageError('');
    try {
      if (draftStorageKey) {
        await AsyncStorage.removeItem(draftStorageKey);
      }
    } catch {
      setPageError('임시 저장 정보를 지우지 못했어요.');
    }
  };

  const requestRecommendation = async () => {
    if (!draft.trip.title || new Date(draft.trip.endAt) <= new Date(draft.trip.startAt)) {
      setPageError('여행 일정을 다시 확인해주세요.');
      return;
    }
    if (!draft.transport) {
      setPageError('이동수단을 하나 선택해주세요.');
      return;
    }
    if (draft.selectedPetIds.length === 0) {
      setPageError('함께 여행할 반려동물을 한 마리 이상 골라주세요.');
      return;
    }
    if (
      (draft.stays.length === 0 || draft.firstDayStart === 'other') &&
      !draft.departureLocation.trim()
    ) {
      setPageError('첫날 여행을 시작할 장소를 입력해주세요.');
      return;
    }
    if (draft.stays.length > 0 && draft.firstDayStart === null) {
      setPageError('첫날 숙소에서 출발할지 다른 장소에서 출발할지 골라주세요.');
      return;
    }
    if (draft.places.length === 0) {
      setPageError('가고 싶은 장소 유형을 한 개 이상 선택해주세요.');
      return;
    }
    const personalization = toPersonalizationPayload(
      draft.priorityMode,
      draft.priorityPreset,
      draft.userCriteria,
    );

    try {
      if (draftStorageKey) {
        await AsyncStorage.setItem(draftStorageKey, serializeDraft(draft, REVIEW_STEP));
      }
    } catch {
      setAutoSaveError('입력 정보를 저장하지 못했어요.');
    }

    const transportMap: Record<string, ServerTransportType> = {
      렌터카: 'rental_car',
      자가용: 'own_car',
      택시: 'taxi',
      도보: 'walk',
    };
    const paceMap: Record<string, ServerTripPace> = {
      여유롭게: 'relaxed',
      적당히: 'normal',
      알차게: 'packed',
    };
    const selectedPets = pets.filter((pet) => draft.selectedPetIds.includes(pet.petId));
    if (selectedPets.length !== draft.selectedPetIds.length) {
      setPageError('선택한 반려동물 정보가 바뀌었어요. 반려동물을 다시 골라주세요.');
      return;
    }
    setIsSubmitting(true);
    setPageError('');
    try {
      const request = {
        title: draft.trip.title,
        startAt: draft.trip.startAt,
        endAt: draft.trip.endAt,
        departureLocation:
          draft.stays.length === 0 || draft.firstDayStart === 'other'
            ? draft.departureLocation.trim()
            : undefined,
        pace: paceMap[draft.pace] ?? 'normal',
        transport: transportMap[draft.transport],
        companionCount: 1,
        preferredTags: draft.places,
        priorityPreset: personalization.priorityPreset,
        userCriteria: personalization.userCriteria,
        petIds: selectedPets.map((pet) => pet.petId),
        stays: draft.stays.map((stay) => toStayRequest(stay, draft.trip)),
      };
      const accepted = await createRouteRecommendation(request);
      await savePendingRoute({ routeId: accepted.routeId, startedAt: Date.now(), request });
      router.push({
        pathname: '/routes/result',
        params: {
          routeId: accepted.routeId,
          petName: selectedPets.map((pet) => pet.name).join(', '),
        },
      });
    } catch (error) {
      const detail = isAxiosError<{ detail?: string }>(error)
        ? error.response?.data?.detail
        : null;
      setPageError(detail ?? '루트 추천을 시작하지 못했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.mobileFrame}>
        <View style={styles.flowHeader}>
          <View accessibilityLabel="오멍가멍 로고" style={styles.flowBrand}>
            <Image resizeMode="contain" source={brandAssets.symbol} style={styles.flowSymbol} />
            <Text style={styles.flowBrandText}>오멍가멍</Text>
          </View>
          <Pressable
            accessibilityLabel="루트 추천 입력 닫기"
            hitSlop={10}
            onPress={() => void closeFlow()}
            style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}
          >
            <Ionicons color={colors.ink} name="close" size={25} />
          </Pressable>
        </View>

        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.flowBody}
        >
          <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
            {openIndex === 0 ? (
              <QuestionStep
                description={
                  tripPhase === 'dates'
                    ? '첫 날은 도착일, 두 번째 날은 출발일로 선택해주세요.'
                    : '여행 이름과 도착·출발 시간을 입력해주세요.'
                }
                icon="calendar-outline"
                title={tripPhase === 'dates' ? '여행 날짜를 골라주세요' : '여행 시간을 알려주세요'}
              >
                {tripPhase === 'dates' ? (
                  <CalendarRangePicker
                    endValue={draft.trip.endAt ? new Date(draft.trip.endAt) : null}
                    onChange={updateTripDates}
                    startValue={draft.trip.startAt ? new Date(draft.trip.startAt) : null}
                  />
                ) : (
                  <View>
                    <View style={styles.formField}>
                      <Text style={styles.formLabel}>여행 이름</Text>
                      <TextInput
                        onChangeText={(title) => updateDraft('trip', { ...draft.trip, title })}
                        placeholder="예: 우리 아이와 첫 제주 여행"
                        placeholderTextColor={theme.textTertiary}
                        style={styles.formInput}
                        value={draft.trip.title}
                      />
                    </View>
                    <View style={styles.inlineDateSummary}>
                      <Ionicons color={colors.orange} name="calendar-outline" size={18} />
                      <Text style={styles.inlineDateSummaryText}>
                        {formatShortDate(draft.trip.startAt)} ~ {formatShortDate(draft.trip.endAt)}
                      </Text>
                      <Text style={styles.durationText}>
                        {formatTripDuration(draft.trip.startAt, draft.trip.endAt)}
                      </Text>
                    </View>
                    <Text style={styles.formGroupTitle}>도착 시간</Text>
                    <TimeNumberInput
                      onChange={(hour, minute) => updateTripTime('startAt', hour, minute)}
                      value={draft.trip.startAt}
                    />
                    <Text style={styles.formGroupTitle}>출발 시간</Text>
                    <TimeNumberInput
                      onChange={(hour, minute) => updateTripTime('endAt', hour, minute)}
                      value={draft.trip.endAt}
                    />
                  </View>
                )}
              </QuestionStep>
            ) : null}

            {openIndex === 1 ? (
              <QuestionStep
                accent={colors.deepMint}
                description="제주에서 주로 이용할 이동수단을 골라주세요."
                icon="car-outline"
                title="이동수단"
              >
                <View style={styles.chipRow}>
                  {draft.transportOptions.slice(0, 4).map((item) => (
                    <ChoiceChip
                      key={item}
                      label={item}
                      onPress={() => updateDraft('transport', item)}
                      selected={draft.transport === item}
                    />
                  ))}
                </View>
              </QuestionStep>
            ) : null}

            {openIndex === 2 ? (
              <QuestionStep
                description="숙소를 알려주면 하루 동선을 더 편하게 정리할 수 있어요."
                icon="bed-outline"
                title="숙소"
              >
                {draft.stays.map((stay) => (
                  <View key={stay.id} style={styles.stayRow}>
                    <View style={styles.stayDayBadge}>
                      <Text style={styles.stayDayText}>{stay.period}</Text>
                    </View>
                    <Pressable onPress={() => openStayEditor(stay)} style={styles.stayCopy}>
                      <Text style={styles.valueLabel}>{stay.name}</Text>
                      <Text style={styles.valueText}>{stay.address || '주소 미입력'}</Text>
                    </Pressable>
                    <Pressable
                      accessibilityLabel={`${stay.name} 삭제`}
                      onPress={() => setPendingStayDelete(stay)}
                    >
                      <Ionicons color={colors.red} name="trash-outline" size={17} />
                    </Pressable>
                  </View>
                ))}
                <Pressable onPress={() => openStayEditor()} style={styles.dashedButton}>
                  <Ionicons color={colors.orange} name="add-circle" size={15} />
                  <Text style={styles.dashedButtonText}>숙소 추가</Text>
                </Pressable>
                {draft.stays.length > 0 ? (
                  <>
                    <Text style={styles.formGroupTitle}>첫날 출발 장소</Text>
                    <View style={styles.chipRow}>
                      <ChoiceChip
                        label="숙소에서 출발"
                        onPress={() => updateDraft('firstDayStart', 'stay')}
                        selected={draft.firstDayStart === 'stay'}
                      />
                      <ChoiceChip
                        label="다른 장소에서 출발"
                        onPress={() => updateDraft('firstDayStart', 'other')}
                        selected={draft.firstDayStart === 'other'}
                      />
                    </View>
                  </>
                ) : null}
                {draft.stays.length === 0 || draft.firstDayStart === 'other' ? (
                  <>
                    <Text style={styles.formGroupTitle}>여행 시작 장소</Text>
                    <View style={styles.chipRow}>
                      {['제주국제공항', '제주항', '서귀포항'].map((place) => (
                        <ChoiceChip
                          key={place}
                          label={place}
                          onPress={() => updateDraft('departureLocation', place)}
                          selected={draft.departureLocation === place}
                        />
                      ))}
                    </View>
                    <TextInput
                      onChangeText={(value) => updateDraft('departureLocation', value)}
                      placeholder="다른 시작 장소 입력"
                      placeholderTextColor={theme.textTertiary}
                      style={styles.formInput}
                      value={draft.departureLocation}
                    />
                  </>
                ) : null}
              </QuestionStep>
            ) : null}

            {openIndex === 3 ? (
              <QuestionStep
                accent={colors.deepMint}
                description="함께 여행할 반려동물의 정보를 확인해주세요."
                icon="paw-outline"
                title="반려동물 정보"
              >
                {isPetsPending ? (
                  <Text style={styles.valueText}>반려동물을 불러오는 중이에요...</Text>
                ) : null}
                {!isPetsPending && pets.length === 0 ? (
                  <Text style={styles.valueText}>먼저 프로필에서 반려동물을 등록해주세요.</Text>
                ) : null}
                {pets.map((pet) => {
                  const selected = draft.selectedPetIds.includes(pet.petId);
                  return (
                    <Pressable
                      key={pet.petId}
                      onPress={() =>
                        updateDraft(
                          'selectedPetIds',
                          selected
                            ? draft.selectedPetIds.filter((id) => id !== pet.petId)
                            : [...draft.selectedPetIds, pet.petId],
                        )
                      }
                      style={[styles.petRow, selected && styles.presetCardSelected]}
                    >
                      <View style={styles.petAvatar}>
                        <Text style={styles.petEmoji}>🐾</Text>
                      </View>
                      <View style={styles.flexOne}>
                        <Text style={styles.petName}>{pet.name}</Text>
                        <Text style={styles.petDescription}>
                          {pet.species} · {pet.size ?? '크기 미입력'}
                        </Text>
                      </View>
                      <Ionicons
                        color={selected ? colors.deepMint : colors.gray}
                        name={selected ? 'checkmark-circle' : 'ellipse-outline'}
                        size={20}
                      />
                    </Pressable>
                  );
                })}
              </QuestionStep>
            ) : null}

            {openIndex === 4 ? (
              <QuestionStep
                description="이번 여행에서 관심 있는 유형을 최대 3개까지 골라주세요."
                icon="location-outline"
                title="가고 싶은 장소 유형"
              >
                <View style={styles.chipRow}>
                  {PLACE_TYPE_OPTIONS.map((item) => (
                    <ChoiceChip
                      key={item}
                      label={item}
                      onPress={() => togglePlaceType(item)}
                      selected={draft.places.includes(item)}
                    />
                  ))}
                </View>
              </QuestionStep>
            ) : null}

            {openIndex === 5 ? (
              <QuestionStep
                accent={colors.deepMint}
                description="하루를 어떤 템포로 여행하고 싶은지 골라주세요."
                icon="speedometer-outline"
                title="여행 속도"
              >
                <View style={styles.paceRow}>
                  {['여유롭게', '적당히', '알차게'].map((item) => (
                    <Pressable
                      key={item}
                      onPress={() => updateDraft('pace', item)}
                      style={[styles.paceButton, draft.pace === item && styles.paceButtonSelected]}
                    >
                      <Text
                        style={[styles.paceText, draft.pace === item && styles.paceTextSelected]}
                      >
                        {item}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </QuestionStep>
            ) : null}

            {openIndex === 6 ? (
              <QuestionStep
                accent={colors.deepMint}
                description={
                  draft.priorityMode === 'manual'
                    ? '중요하게 생각하는 기준을 최대 3개까지 골라주세요.'
                    : '원하는 여행 방식을 하나만 골라주세요.'
                }
                icon="options-outline"
                title="이번 여행에서 무엇이 중요한가요?"
              >
                {draft.priorityMode === 'manual' ? (
                  <>
                    <View style={styles.chipRow}>
                      {USER_CRITERIA_OPTIONS.map((criterion) => (
                        <ChoiceChip
                          key={criterion.value}
                          label={criterion.label}
                          onPress={() => toggleUserCriterion(criterion.value)}
                          selected={draft.userCriteria.includes(criterion.value)}
                        />
                      ))}
                    </View>
                    <Pressable
                      onPress={() => switchPriorityMode('preset')}
                      style={styles.modeSwitchButton}
                    >
                      <Ionicons color={colors.deepMint} name="flash-outline" size={17} />
                      <Text style={styles.modeSwitchText}>빠르게 고르기</Text>
                    </Pressable>
                  </>
                ) : (
                  <>
                    <View style={styles.presetList}>
                      {PRIORITY_PRESETS.map((preset) => {
                        const selected = draft.priorityPreset === preset.value;
                        return (
                          <Pressable
                            accessibilityRole="radio"
                            accessibilityState={{ selected }}
                            key={preset.value}
                            onPress={() =>
                              setDraft((current) => ({
                                ...current,
                                priorityPreset: preset.value,
                                userCriteria: [],
                              }))
                            }
                            style={[styles.presetCard, selected && styles.presetCardSelected]}
                          >
                            <View style={styles.presetTitleRow}>
                              <Text
                                style={[styles.presetTitle, selected && styles.presetTitleSelected]}
                              >
                                {preset.label}
                              </Text>
                              <Ionicons
                                color={selected ? colors.orange : theme.textTertiary}
                                name={selected ? 'radio-button-on' : 'radio-button-off'}
                                size={20}
                              />
                            </View>
                            <Text style={styles.presetDescription}>{preset.description}</Text>
                          </Pressable>
                        );
                      })}
                    </View>
                    <Pressable
                      onPress={() => switchPriorityMode('manual')}
                      style={styles.modeSwitchButton}
                    >
                      <Ionicons color={colors.deepMint} name="options-outline" size={17} />
                      <Text style={styles.modeSwitchText}>중요한 기준 직접 고르기</Text>
                    </Pressable>
                  </>
                )}
              </QuestionStep>
            ) : null}

            {isReviewStep ? (
              <View style={styles.reviewSection}>
                <Text style={styles.reviewEyebrow}>입력 정보 확인</Text>
                <Text style={styles.reviewTitle}>
                  {pets
                    .filter((pet) => draft.selectedPetIds.includes(pet.petId))
                    .map((pet) => pet.name)
                    .join(', ') || '반려동물'}
                  와 함께하는 {draft.trip.title}
                </Text>
                <Text style={styles.reviewDescription}>
                  추천 전에 입력한 내용을 한 번만 확인해주세요.
                </Text>
                <View style={styles.reviewList}>
                  {STEPS.map((step, index) => (
                    <Pressable
                      key={step.key}
                      onPress={() => {
                        setReturnToReview(true);
                        if (index === 0) setTripPhase('dates');
                        setOpenIndex(index);
                      }}
                      style={styles.reviewRow}
                    >
                      <View style={styles.reviewRowCopy}>
                        <Text style={styles.reviewRowLabel}>
                          {
                            [
                              '여행 일정',
                              '이동수단',
                              '숙소',
                              '반려동물',
                              '가고 싶은 장소 유형',
                              '여행 속도',
                              '추천 스타일',
                            ][index]
                          }
                        </Text>
                        <Text numberOfLines={1} style={styles.reviewRowValue}>
                          {stepSummaries[index]}
                        </Text>
                      </View>
                      <Text style={styles.reviewEditText}>수정</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            ) : null}

            {autoSaveError ? (
              <View accessibilityRole="alert" style={styles.pageErrorBox}>
                <Ionicons color={colors.red} name="alert-circle" size={17} />
                <Text style={styles.pageErrorText}>{autoSaveError}</Text>
              </View>
            ) : null}

            {pageError ? (
              <View accessibilityRole="alert" style={styles.pageErrorBox}>
                <Ionicons color={colors.red} name="alert-circle" size={17} />
                <Text style={styles.pageErrorText}>{pageError}</Text>
              </View>
            ) : null}

            {!isReviewStep && STEPS[openIndex]?.optional ? (
              <Pressable onPress={skipCurrentStep} style={styles.inlineSkipButton}>
                <Text style={styles.inlineSkipText}>건너뛰기</Text>
              </Pressable>
            ) : null}

            {isReviewStep ? (
              <Pressable onPress={() => setResetConfirmOpen(true)} style={styles.resetButton}>
                <Text style={styles.resetText}>처음부터 다시 입력</Text>
              </Pressable>
            ) : null}
          </ScrollView>

          <View style={styles.footerNavigation}>
            {!isReviewStep && (openIndex > 0 || tripPhase === 'details') ? (
              <Pressable
                accessibilityLabel="이전 단계"
                onPress={() => {
                  setPageError('');
                  if (openIndex === 0 && tripPhase === 'details') {
                    setTripPhase('dates');
                  } else {
                    setOpenIndex((current) => Math.max(0, current - 1));
                  }
                }}
                style={({ pressed }) => [styles.footerBackButton, pressed && styles.pressed]}
              >
                <Ionicons color={colors.gray} name="chevron-back" size={18} />
                <Text style={styles.footerBackText}>이전</Text>
              </Pressable>
            ) : null}
            <Pressable
              disabled={isSubmitting}
              onPress={() => (isReviewStep ? void requestRecommendation() : goNextStep(openIndex))}
              style={({ pressed }) => [styles.footerNextButton, pressed && styles.pressed]}
              testID={isReviewStep ? 'recommend-route-button' : 'route-next-button'}
            >
              {isReviewStep ? <Ionicons color={colors.white} name="paw" size={18} /> : null}
              <Text style={styles.footerNextText}>
                {isSubmitting
                  ? '추천을 준비하는 중...'
                  : isReviewStep
                    ? '루트 추천받기'
                    : nextStepLabel(openIndex)}
              </Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </View>

      <Modal
        animationType="slide"
        onRequestClose={closeEditor}
        transparent
        visible={editTarget !== null}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalBackdrop}
        >
          <Pressable onPress={closeEditor} style={styles.modalDismissArea} />
          <View style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>숙소 정보</Text>

            {editTarget === 'stay' ? (
              <>
                <View style={styles.formField}>
                  <Text style={styles.formLabel}>등록된 숙소 찾기</Text>
                  <Text style={styles.formHelper}>
                    숙소를 선택하면 저장된 주소와 위치를 루트 추천에 반영해요.
                  </Text>
                  <View style={styles.staySearchRow}>
                    <TextInput
                      onChangeText={setStaySearchQuery}
                      onSubmitEditing={() => void loadStayOptions(staySearchQuery)}
                      placeholder="숙소 이름으로 검색"
                      placeholderTextColor={theme.textTertiary}
                      returnKeyType="search"
                      style={styles.staySearchInput}
                      value={staySearchQuery}
                    />
                    <Pressable
                      accessibilityLabel="숙소 검색"
                      disabled={staySearchLoading}
                      onPress={() => void loadStayOptions(staySearchQuery)}
                      style={styles.staySearchButton}
                    >
                      <Ionicons color={colors.white} name="search" size={20} />
                    </Pressable>
                  </View>
                  {staySearchLoading ? (
                    <Text style={styles.staySearchMessage}>숙소를 찾고 있어요…</Text>
                  ) : staySearchError ? (
                    <Text style={styles.staySearchError}>{staySearchError}</Text>
                  ) : staySearchResults.length === 0 ? (
                    <Text style={styles.staySearchMessage}>
                      검색 결과가 없어요. 아래에서 직접 입력할 수 있어요.
                    </Text>
                  ) : (
                    <ScrollView
                      keyboardShouldPersistTaps="handled"
                      nestedScrollEnabled
                      style={styles.staySearchList}
                    >
                      {staySearchResults.map((place) => {
                        const selected = formValues.placeId === place.id;
                        return (
                          <Pressable
                            accessibilityRole="button"
                            accessibilityState={{ selected }}
                            key={place.id}
                            onPress={() => {
                              setFormValues((current) => ({
                                ...current,
                                placeId: place.id,
                                name: place.name,
                                address: place.address,
                              }));
                              setFormError('');
                            }}
                            style={[
                              styles.staySearchItem,
                              selected && styles.staySearchItemSelected,
                            ]}
                          >
                            <View style={styles.staySearchItemCopy}>
                              <Text style={styles.staySearchItemName}>{place.name}</Text>
                              <Text numberOfLines={1} style={styles.staySearchItemAddress}>
                                {place.address || '주소 정보 없음'}
                              </Text>
                            </View>
                            {selected ? (
                              <Ionicons color={colors.deepMint} name="checkmark-circle" size={22} />
                            ) : null}
                          </Pressable>
                        );
                      })}
                    </ScrollView>
                  )}
                </View>

                <View style={styles.manualStayDivider}>
                  <View style={styles.manualStayDividerLine} />
                  <Text style={styles.manualStayDividerText}>목록에 없다면 직접 입력</Text>
                  <View style={styles.manualStayDividerLine} />
                </View>
                <FormInput
                  label="숙소 이름"
                  name="name"
                  onChange={() => setFormValues((current) => ({ ...current, placeId: '' }))}
                  setValues={setFormValues}
                  values={formValues}
                />
                <View style={styles.formField}>
                  <Text style={styles.formLabel}>숙박 일차</Text>
                  <Text style={styles.formHelper}>
                    여행 일정 중 이 숙소에서 머무는 밤을 선택해주세요.
                  </Text>
                  <View style={styles.stayPeriodChips}>
                    {stayNightOptions.map((option) => {
                      const selected = parseStayPeriods(formValues.period ?? '').includes(
                        option.value,
                      );
                      return (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityState={{ selected }}
                          key={option.value}
                          onPress={() => toggleStayPeriod(option.value)}
                          style={[styles.stayPeriodChip, selected && styles.stayPeriodChipSelected]}
                        >
                          <Text
                            style={[
                              styles.stayPeriodChipTitle,
                              selected && styles.stayPeriodChipTitleSelected,
                            ]}
                          >
                            {option.label}
                          </Text>
                          <Text
                            style={[
                              styles.stayPeriodChipDate,
                              selected && styles.stayPeriodChipDateSelected,
                            ]}
                          >
                            {option.dateLabel}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </View>
                  {stayNightOptions.length === 0 ? (
                    <Text style={styles.emptyStayPeriod}>숙박이 없는 당일 여행이에요.</Text>
                  ) : null}
                </View>
                <FormInput
                  label="주소"
                  name="address"
                  onChange={() => setFormValues((current) => ({ ...current, placeId: '' }))}
                  setValues={setFormValues}
                  values={formValues}
                />
              </>
            ) : null}

            {formError ? (
              <View style={styles.formErrorBox}>
                <Ionicons color={colors.red} name="alert-circle" size={16} />
                <Text style={styles.formErrorText}>{formError}</Text>
              </View>
            ) : null}

            <View style={styles.modalActions}>
              <Pressable onPress={closeEditor} style={styles.cancelButton}>
                <Text style={styles.cancelText}>취소</Text>
              </Pressable>
              <Pressable onPress={saveEditor} style={styles.saveButton}>
                <Text style={styles.saveText}>저장</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      <ConfirmModal
        confirmLabel="삭제"
        description={`${pendingStayDelete?.name ?? ''} 정보를 삭제할까요?`}
        onCancel={() => setPendingStayDelete(null)}
        onConfirm={() => {
          if (pendingStayDelete) {
            updateDraft(
              'stays',
              draft.stays.filter((item) => item.id !== pendingStayDelete.id),
            );
          }
          setPendingStayDelete(null);
        }}
        title="숙소 삭제"
        tone="destructive"
        visible={pendingStayDelete !== null}
      />

      <ConfirmModal
        confirmLabel="처음부터 입력"
        description="자동 저장된 내용까지 지우고 처음 화면으로 돌아갈까요?"
        onCancel={() => setResetConfirmOpen(false)}
        onConfirm={() => void resetAll()}
        title="입력 초기화"
        tone="destructive"
        visible={resetConfirmOpen}
      />
    </SafeAreaView>
  );
}

function TimeNumberInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (hour: number, minute: number) => void;
}) {
  const currentValue = new Date(value);
  const [hour, setHour] = useState(String(currentValue.getHours()).padStart(2, '0'));
  const [minute, setMinute] = useState(String(currentValue.getMinutes()).padStart(2, '0'));

  const commit = (nextHour = hour, nextMinute = minute) => {
    const normalizedHour = Math.min(23, Math.max(0, Number(nextHour) || 0));
    const normalizedMinute = Math.min(59, Math.max(0, Number(nextMinute) || 0));
    setHour(String(normalizedHour).padStart(2, '0'));
    setMinute(String(normalizedMinute).padStart(2, '0'));
    onChange(normalizedHour, normalizedMinute);
  };

  return (
    <View accessibilityLabel="시간 숫자 입력" style={styles.timeNumberGroup}>
      <Ionicons color={colors.gray} name="time-outline" size={18} />
      <TextInput
        accessibilityLabel="시"
        inputMode="numeric"
        keyboardType="number-pad"
        maxLength={2}
        onBlur={() => commit()}
        onChangeText={(text) => setHour(text.replace(/\D/g, ''))}
        selectTextOnFocus
        style={styles.timeNumberInput}
        value={hour}
      />
      <Text style={styles.timeUnitText}>시</Text>
      <Text style={styles.timeColon}>:</Text>
      <TextInput
        accessibilityLabel="분"
        inputMode="numeric"
        keyboardType="number-pad"
        maxLength={2}
        onBlur={() => commit()}
        onChangeText={(text) => setMinute(text.replace(/\D/g, ''))}
        selectTextOnFocus
        style={styles.timeNumberInput}
        value={minute}
      />
      <Text style={styles.timeUnitText}>분</Text>
    </View>
  );
}

function FormInput({
  label,
  name,
  onChange,
  values,
  setValues,
}: {
  label: string;
  name: string;
  onChange?: () => void;
  values: Record<string, string>;
  setValues: React.Dispatch<React.SetStateAction<Record<string, string>>>;
}) {
  return (
    <View style={styles.formField}>
      <Text style={styles.formLabel}>{label}</Text>
      <TextInput
        onChangeText={(value) => {
          onChange?.();
          setValues((current) => ({ ...current, [name]: value }));
        }}
        placeholder={`${label} 입력`}
        placeholderTextColor={theme.textTertiary}
        style={styles.formInput}
        value={values[name] ?? ''}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.white, flex: 1 },
  mobileFrame: { backgroundColor: colors.white, flex: 1 },
  flowBody: { flex: 1 },
  flowHeader: {
    alignItems: 'center',
    borderBottomColor: theme.divider,
    borderBottomWidth: 1,
    flexDirection: 'row',
    height: 56,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
  },
  flowBrand: { alignItems: 'center', flexDirection: 'row', gap: 7 },
  flowSymbol: { height: 30, width: 27 },
  flowBrandText: {
    color: colors.orange,
    fontSize: 19,
    fontWeight: '900',
    letterSpacing: -0.8,
  },
  closeButton: {
    alignItems: 'center',
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  content: {
    backgroundColor: colors.white,
    flexGrow: 1,
    paddingBottom: spacing.lg,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.lg,
  },
  questionStep: { flex: 1 },
  questionIcon: {
    alignItems: 'center',
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    marginBottom: spacing.md,
    width: 44,
  },
  questionHeading: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
  },
  questionCopy: { flex: 1, paddingRight: spacing.sm },
  questionTitle: {
    color: colors.ink,
    fontSize: typography.title.fontSize,
    fontWeight: '900',
  },
  questionDescription: {
    color: colors.gray,
    fontSize: typography.label.fontSize,
    lineHeight: 20,
    marginTop: spacing.xs,
  },
  footerNavigation: {
    alignItems: 'center',
    backgroundColor: colors.white,
    borderTopColor: theme.divider,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  footerBackButton: {
    alignItems: 'center',
    backgroundColor: colors.white,
    borderColor: theme.divider,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    minHeight: 52,
    width: 112,
  },
  footerBackText: { color: colors.gray, fontSize: typography.body.fontSize, fontWeight: '800' },
  footerNextButton: {
    alignItems: 'center',
    backgroundColor: colors.orange,
    borderRadius: radius.lg,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
    minHeight: 52,
  },
  footerNextText: {
    color: colors.white,
    fontSize: typography.body.fontSize,
    fontWeight: '800',
  },
  inlineSkipButton: {
    alignItems: 'center',
    alignSelf: 'center',
    justifyContent: 'center',
    marginTop: spacing.md,
    minHeight: 40,
  },
  inlineSkipText: {
    color: theme.textTertiary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
    textDecorationLine: 'underline',
  },
  editButton: { alignItems: 'center', flexDirection: 'row', gap: 3, padding: 5 },
  editText: { color: colors.gray, fontSize: typography.label.fontSize, fontWeight: '600' },
  valueBox: {
    alignItems: 'center',
    backgroundColor: theme.surface,
    borderColor: theme.basaltSoft,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: spacing.sm + 4,
    paddingVertical: spacing.sm + 4,
  },
  flexOne: { flex: 1 },
  valueLabel: { color: colors.ink, fontSize: typography.body.fontSize, fontWeight: '800' },
  valueText: { color: colors.gray, fontSize: typography.label.fontSize, marginTop: 4 },
  durationText: {
    color: colors.deepMint,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '800',
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  choiceChip: {
    alignItems: 'center',
    backgroundColor: theme.neutralGray,
    borderColor: theme.basaltSoft,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs + 2,
    minHeight: 42,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  choiceChipSelected: { backgroundColor: colors.orange, borderColor: colors.orange },
  choiceChipText: { color: colors.gray, fontSize: typography.subtitle.fontSize, fontWeight: '700' },
  choiceChipTextSelected: { color: colors.white },
  addRow: {
    alignItems: 'center',
    borderColor: theme.seaSoft,
    borderRadius: radius.md,
    borderStyle: 'dashed',
    borderWidth: 1,
    flexDirection: 'row',
    marginTop: spacing.sm + 2,
    paddingLeft: spacing.sm + 4,
  },
  addInput: {
    color: colors.ink,
    flex: 1,
    fontSize: typography.subtitle.fontSize,
    minHeight: 46,
    outlineStyle: 'none',
  } as never,
  inlineAddButton: {
    alignItems: 'center',
    backgroundColor: colors.deepMint,
    borderRadius: radius.sm,
    height: 38,
    justifyContent: 'center',
    marginRight: spacing.xs + 2,
    width: 40,
  },
  stayRow: {
    alignItems: 'center',
    backgroundColor: theme.surface,
    borderColor: theme.basaltSoft,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 2,
    marginBottom: spacing.sm,
    padding: spacing.sm + 4,
  },
  stayDayBadge: {
    backgroundColor: theme.primarySoft,
    borderRadius: radius.sm - 2,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs + 1,
  },
  stayDayText: { color: colors.orange, fontSize: typography.micro.fontSize, fontWeight: '800' },
  stayCopy: { flex: 1 },
  dashedButton: {
    alignItems: 'center',
    borderColor: theme.primarySoftStrong,
    borderRadius: radius.md,
    borderStyle: 'dashed',
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs + 2,
    justifyContent: 'center',
    minHeight: 46,
  },
  dashedButtonText: {
    color: colors.orange,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  petRow: {
    alignItems: 'center',
    backgroundColor: theme.surface,
    borderColor: theme.basaltSoft,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 3,
    padding: spacing.sm + 4,
  },
  petAvatar: {
    alignItems: 'center',
    backgroundColor: colors.cream,
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  petEmoji: { fontSize: 25 },
  petName: { color: colors.ink, fontSize: typography.body.fontSize, fontWeight: '800' },
  petDescription: { color: colors.gray, fontSize: typography.label.fontSize, marginTop: 3 },
  paceRow: { flexDirection: 'row', gap: 7 },
  paceButton: {
    alignItems: 'center',
    borderColor: theme.divider,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    minHeight: 44,
    justifyContent: 'center',
    paddingVertical: spacing.sm + 2,
  },
  paceButtonSelected: {
    backgroundColor: theme.seaSoftLight,
    borderColor: colors.mint,
    borderWidth: 1.5,
  },
  paceText: { color: colors.gray, fontSize: typography.subtitle.fontSize, fontWeight: '700' },
  paceTextSelected: { color: colors.deepMint },
  presetList: { gap: spacing.sm },
  presetCard: {
    borderColor: theme.divider,
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing.sm + 3,
  },
  presetCardSelected: {
    backgroundColor: theme.primarySoft,
    borderColor: colors.orange,
    borderWidth: 1.5,
  },
  presetTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  presetTitle: { color: colors.ink, fontSize: typography.subtitle.fontSize, fontWeight: '800' },
  presetTitleSelected: { color: colors.orange },
  presetDescription: {
    color: colors.gray,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
    marginTop: spacing.xs,
  },
  modeSwitchButton: {
    alignItems: 'center',
    alignSelf: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
    marginTop: spacing.lg,
    minHeight: 42,
    paddingHorizontal: spacing.md,
  },
  modeSwitchText: {
    color: colors.deepMint,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  reviewSection: { flex: 1 },
  reviewEyebrow: {
    color: colors.deepMint,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  reviewTitle: {
    color: colors.ink,
    fontSize: typography.title.fontSize + 4,
    fontWeight: '900',
    lineHeight: typography.title.fontSize + 11,
    marginTop: spacing.sm,
  },
  reviewDescription: {
    color: colors.gray,
    fontSize: typography.body.fontSize,
    lineHeight: 24,
    marginTop: spacing.sm,
  },
  reviewList: { borderTopColor: theme.divider, borderTopWidth: 1, marginTop: spacing.xl },
  reviewRow: {
    alignItems: 'center',
    borderBottomColor: theme.divider,
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 76,
    paddingVertical: spacing.md,
  },
  reviewRowCopy: { flex: 1, paddingRight: spacing.sm },
  reviewRowLabel: { color: colors.gray, fontSize: typography.label.fontSize },
  reviewRowValue: {
    color: colors.ink,
    fontSize: typography.body.fontSize + 1,
    fontWeight: '800',
    marginTop: 5,
  },
  reviewEditText: {
    color: colors.deepMint,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  pageErrorBox: {
    alignItems: 'center',
    backgroundColor: theme.errorBg,
    borderRadius: 10,
    flexDirection: 'row',
    gap: 6,
    marginTop: 10,
    padding: 10,
  },
  pageErrorText: {
    color: colors.red,
    flex: 1,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  resetButton: {
    alignItems: 'center',
    alignSelf: 'center',
    justifyContent: 'center',
    marginTop: spacing.md,
    minHeight: 40,
    paddingHorizontal: spacing.md,
  },
  resetText: {
    color: theme.textTertiary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  modalBackdrop: { backgroundColor: overlayColors.scrim, flex: 1, justifyContent: 'flex-end' },
  modalDismissArea: { flex: 1 },
  modalSheet: {
    alignSelf: 'center',
    backgroundColor: colors.white,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxWidth: 430,
    padding: 20,
    width: '100%',
  },
  modalHandle: {
    alignSelf: 'center',
    backgroundColor: theme.divider,
    borderRadius: 2,
    height: 4,
    marginBottom: 16,
    width: 42,
  },
  modalTitle: {
    color: colors.ink,
    fontSize: typography.title.fontSize,
    fontWeight: '900',
    marginBottom: 14,
  },
  formField: { marginBottom: 11 },
  formLabel: {
    color: colors.ink,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
    marginBottom: 6,
  },
  formHelper: {
    color: colors.gray,
    fontSize: typography.caption.fontSize,
    marginBottom: 9,
    marginTop: -2,
  },
  formInput: {
    borderColor: colors.line,
    borderRadius: 10,
    borderWidth: 1,
    color: colors.ink,
    fontSize: typography.body.fontSize,
    minHeight: 44,
    outlineStyle: 'none',
    paddingHorizontal: 12,
  } as never,
  staySearchRow: { flexDirection: 'row', gap: 8 },
  staySearchInput: {
    borderColor: colors.line,
    borderRadius: 10,
    borderWidth: 1,
    color: colors.ink,
    flex: 1,
    fontSize: typography.body.fontSize,
    minHeight: 44,
    outlineStyle: 'none',
    paddingHorizontal: 12,
  } as never,
  staySearchButton: {
    alignItems: 'center',
    backgroundColor: colors.deepMint,
    borderRadius: 10,
    justifyContent: 'center',
    width: 48,
  },
  staySearchList: {
    borderColor: theme.divider,
    borderRadius: 10,
    borderWidth: 1,
    marginTop: 8,
    maxHeight: 170,
  },
  staySearchItem: {
    alignItems: 'center',
    borderBottomColor: theme.divider,
    borderBottomWidth: 1,
    flexDirection: 'row',
    minHeight: 58,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  staySearchItemSelected: { backgroundColor: theme.seaSoftLight },
  staySearchItemCopy: { flex: 1, paddingRight: 8 },
  staySearchItemName: {
    color: colors.ink,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  staySearchItemAddress: {
    color: colors.gray,
    fontSize: typography.caption.fontSize,
    marginTop: 3,
  },
  staySearchMessage: {
    color: colors.gray,
    fontSize: typography.caption.fontSize,
    marginTop: 8,
  },
  staySearchError: {
    color: colors.red,
    fontSize: typography.caption.fontSize,
    marginTop: 8,
  },
  manualStayDivider: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
    marginTop: 2,
  },
  manualStayDividerLine: { backgroundColor: theme.divider, flex: 1, height: 1 },
  manualStayDividerText: { color: theme.textTertiary, fontSize: typography.caption.fontSize },
  stayPeriodChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  stayPeriodChip: {
    backgroundColor: theme.neutralGray,
    borderColor: theme.divider,
    borderRadius: 10,
    borderWidth: 1,
    minWidth: 104,
    paddingHorizontal: 11,
    paddingVertical: 9,
  },
  stayPeriodChipSelected: {
    backgroundColor: theme.primarySoft,
    borderColor: colors.orange,
    borderWidth: 1.5,
  },
  stayPeriodChipTitle: {
    color: colors.gray,
    fontSize: typography.label.fontSize,
    fontWeight: '900',
  },
  stayPeriodChipTitleSelected: { color: colors.orange },
  stayPeriodChipDate: {
    color: theme.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: '600',
    marginTop: 3,
  },
  stayPeriodChipDateSelected: { color: theme.primaryDeep },
  emptyStayPeriod: {
    backgroundColor: colors.lightGray,
    borderRadius: 9,
    color: colors.gray,
    fontSize: typography.caption.fontSize,
    padding: 11,
  },
  formGroupTitle: {
    color: colors.ink,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '800',
    marginBottom: 7,
    marginTop: 2,
  },
  inlineDateSummary: {
    alignItems: 'center',
    backgroundColor: theme.primarySoft,
    borderRadius: 11,
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
    padding: 12,
  },
  inlineDateSummaryText: {
    color: colors.ink,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  timeNumberGroup: {
    alignItems: 'center',
    borderColor: colors.line,
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 8,
    width: '100%',
  },
  timeNumberInput: {
    color: colors.ink,
    fontSize: typography.body.fontSize,
    fontWeight: '800',
    minWidth: 28,
    outlineStyle: 'none',
    paddingHorizontal: 2,
    paddingVertical: 8,
    textAlign: 'center',
  } as never,
  timeUnitText: { color: colors.gray, fontSize: typography.caption.fontSize },
  timeColon: {
    color: colors.gray,
    fontSize: typography.body.fontSize,
    fontWeight: '800',
    marginHorizontal: 2,
  },
  modalActions: { flexDirection: 'row', gap: 9, marginTop: 8 },
  cancelButton: {
    alignItems: 'center',
    borderColor: colors.line,
    borderRadius: 11,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 46,
  },
  cancelText: { color: colors.gray, fontSize: typography.body.fontSize, fontWeight: '800' },
  saveButton: {
    alignItems: 'center',
    backgroundColor: colors.orange,
    borderRadius: 11,
    flex: 1.4,
    justifyContent: 'center',
    minHeight: 46,
  },
  saveText: { color: colors.white, fontSize: typography.body.fontSize, fontWeight: '900' },
  formErrorBox: {
    alignItems: 'center',
    backgroundColor: theme.errorBg,
    borderRadius: 9,
    flexDirection: 'row',
    gap: 6,
    marginBottom: 4,
    padding: 9,
  },
  formErrorText: {
    color: colors.red,
    flex: 1,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  pressed: { opacity: 0.72 },
});

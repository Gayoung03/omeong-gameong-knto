import Ionicons from '@expo/vector-icons/Ionicons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  Alert,
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

import {
  CalendarPicker,
  WheelTimePicker,
} from '../components/InlineDateTimePicker';
import { RouteBottomNavigation } from '../components/RouteBottomNavigation';
import { formatTripDuration } from '../utils/tripDuration';

const DRAFT_KEY = 'route-input-draft';

const colors = {
  orange: '#FF7A00',
  mint: '#12B89B',
  deepMint: '#07967E',
  ink: '#292B2E',
  gray: '#757A80',
  lightGray: '#F6F7F8',
  line: '#E8EAEC',
  white: '#FFFFFF',
  cream: '#FFF8EE',
  red: '#E95858',
};

type Trip = { title: string; startAt: string; endAt: string };
type Stay = { id: string; name: string; period: string; address: string };
type Pet = { name: string; species: string; size: string; weight: string };
type EditTarget = 'trip' | 'pet' | 'stay' | null;
type PickerTarget = 'start-date' | 'start-time' | 'end-date' | 'end-time' | null;
type UtilityModal = 'notifications' | 'profile' | 'later' | null;

type RouteDraft = {
  trip: Trip;
  transportOptions: string[];
  transport: string;
  stays: Stay[];
  pet: Pet;
  places: string[];
  placeOptions: string[];
  pace: string;
};

const initialDraft: RouteDraft = {
  trip: {
    title: '제주 여행',
    startAt: new Date(2026, 7, 18, 10, 0).toISOString(),
    endAt: new Date(2026, 7, 20, 18, 0).toISOString(),
  },
  transportOptions: ['렌터카', '택시', '대중교통'],
  transport: '렌터카',
  stays: [
    { id: 'stay-1', name: '애월 오션펜션', period: '1~2일차', address: '제주시 애월읍' },
  ],
  pet: { name: '몽이', species: '강아지', size: '소형', weight: '4.2kg' },
  places: ['바다', '카페', '오름'],
  placeOptions: ['바다', '카페', '산책로', '실내 관광지', '오름'],
  pace: '여유롭게',
};

const formatDate = (iso: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(iso));

const formatTime = (iso: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso));

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
  return isContinuous ? `${days[0]}~${days.at(-1)}일차` : days.map((day) => `${day}일차`).join(', ');
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
        <Text style={[styles.choiceChipText, selected && styles.choiceChipTextSelected]}>{label}</Text>
      </Pressable>
      {onDelete ? (
        <Pressable accessibilityLabel={`${label} 삭제`} hitSlop={8} onPress={onDelete}>
          <Ionicons
            color={selected ? colors.white : colors.gray}
            name="close-circle"
            size={14}
          />
        </Pressable>
      ) : null}
    </View>
  );
}

function Section({
  icon,
  title,
  children,
  onEdit,
  actionLabel = '수정',
  accent = colors.orange,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  children: React.ReactNode;
  onEdit?: () => void;
  actionLabel?: string;
  accent?: string;
}) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeading}>
        <View style={styles.sectionTitleWrap}>
          <View style={[styles.sectionIcon, { backgroundColor: `${accent}16` }]}>
            <Ionicons color={accent} name={icon} size={19} />
          </View>
          <Text style={styles.sectionTitle}>{title}</Text>
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

function AddRow({
  value,
  placeholder,
  onChangeText,
  onAdd,
}: {
  value: string;
  placeholder: string;
  onChangeText: (value: string) => void;
  onAdd: () => void;
}) {
  return (
    <View style={styles.addRow}>
      <TextInput
        onChangeText={onChangeText}
        onSubmitEditing={onAdd}
        placeholder={placeholder}
        placeholderTextColor="#A5A9AE"
        returnKeyType="done"
        style={styles.addInput}
        value={value}
      />
      <Pressable accessibilityLabel="추가" onPress={onAdd} style={styles.inlineAddButton}>
        <Ionicons color={colors.white} name="add" size={18} />
      </Pressable>
    </View>
  );
}

export function RouteInputScreen() {
  const router = useRouter();
  const [draft, setDraft] = useState<RouteDraft>(initialDraft);
  const [editTarget, setEditTarget] = useState<EditTarget>(null);
  const [pickerTarget, setPickerTarget] = useState<PickerTarget>(null);
  const [editingStayId, setEditingStayId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [newTransport, setNewTransport] = useState('');
  const [newPlace, setNewPlace] = useState('');
  const [notice, setNotice] = useState('');
  const [utilityModal, setUtilityModal] = useState<UtilityModal>(null);
  const [formError, setFormError] = useState('');
  const [pageError, setPageError] = useState('');
  const stayNightOptions = getStayNightOptions(draft.trip);

  useEffect(() => {
    void AsyncStorage.getItem(DRAFT_KEY).then((saved) => {
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as Partial<RouteDraft>;
          const savedTrip = parsed.trip as Trip | undefined;
          setDraft({
            ...initialDraft,
            ...parsed,
            trip:
              savedTrip?.startAt && savedTrip?.endAt
                ? savedTrip
                : initialDraft.trip,
          });
          setNotice('이전에 임시 저장한 정보를 불러왔어요.');
        } catch {
          setPageError('임시 저장 정보를 불러오지 못했어요. 새로 입력해주세요.');
        }
      }
    });
  }, []);

  const updateDraft = <K extends keyof RouteDraft>(key: K, value: RouteDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setNotice('');
    setPageError('');
  };

  const openTripEditor = () => {
    setFormError('');
    setFormValues(draft.trip);
    setPickerTarget(null);
    setEditTarget('trip');
  };

  const openPetEditor = () => {
    setFormError('');
    setFormValues(draft.pet);
    setEditTarget('pet');
  };

  const openStayEditor = (stay?: Stay) => {
    setFormError('');
    setEditingStayId(stay?.id ?? null);
    setFormValues(
      stay ?? { id: '', name: '', period: '', address: '' },
    );
    setEditTarget('stay');
  };

  const toggleStayPeriod = (period: string) => {
    const selectedPeriods = parseStayPeriods(formValues.period ?? '');
    const nextPeriods = selectedPeriods.includes(period)
      ? selectedPeriods.filter((selected) => selected !== period)
      : [...selectedPeriods, period];
    setFormValues((values) => ({ ...values, period: formatStayPeriods(nextPeriods) }));
    setFormError('');
  };

  const updateTripDateTime = (target: Exclude<PickerTarget, null>, selectedDate: Date) => {
    const field = target.startsWith('start') ? 'startAt' : 'endAt';
    const current = new Date(formValues[field]);

    if (target.endsWith('date')) {
      current.setFullYear(
        selectedDate.getFullYear(),
        selectedDate.getMonth(),
        selectedDate.getDate(),
      );
    } else {
      current.setHours(selectedDate.getHours(), selectedDate.getMinutes(), 0, 0);
    }

    setFormValues((values) => ({ ...values, [field]: current.toISOString() }));
    if (Platform.OS === 'android') setPickerTarget(null);
  };

  const closeEditor = () => {
    setEditTarget(null);
    setPickerTarget(null);
    setEditingStayId(null);
    setFormValues({});
    setFormError('');
  };

  const saveEditor = () => {
    if (editTarget === 'trip') {
      if (!formValues.title || !formValues.startAt || !formValues.endAt) {
        setFormError('여행 이름과 도착·출발 일시를 모두 입력해주세요.');
        return;
      }
      if (new Date(formValues.endAt) <= new Date(formValues.startAt)) {
        setFormError('출발 일시는 도착 일시보다 이후여야 해요.');
        return;
      }
      const nextTrip = {
        title: formValues.title,
        startAt: formValues.startAt,
        endAt: formValues.endAt,
      };
      const validPeriods = new Set(getStayNightOptions(nextTrip).map((option) => option.value));
      let adjustedStayCount = 0;
      const nextStays = draft.stays.flatMap((stay) => {
        const nextPeriod = formatStayPeriods(
          parseStayPeriods(stay.period).filter((period) => validPeriods.has(period)),
        );
        if (nextPeriod === stay.period) return [stay];
        adjustedStayCount += 1;
        return nextPeriod ? [{ ...stay, period: nextPeriod }] : [];
      });

      setDraft((current) => ({ ...current, stays: nextStays, trip: nextTrip }));
      setPageError('');
      setNotice(
        adjustedStayCount > 0
          ? '여행 기간에 맞지 않는 숙박 일차를 자동으로 정리했어요.'
          : '',
      );
    }

    if (editTarget === 'pet') {
      if (!formValues.name || !formValues.species) {
        setFormError('반려동물 이름과 종류를 입력해주세요.');
        return;
      }
      updateDraft('pet', {
        name: formValues.name,
        species: formValues.species,
        size: formValues.size,
        weight: formValues.weight,
      });
    }

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
        id: editingStayId ?? `stay-${Date.now()}`,
        name: formValues.name,
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

  const addTransport = () => {
    const value = newTransport.trim();
    if (!value || draft.transportOptions.includes(value)) return;
    updateDraft('transportOptions', [...draft.transportOptions, value]);
    updateDraft('transport', value);
    setNewTransport('');
  };

  const addPlace = () => {
    const value = newPlace.trim();
    if (!value) return;
    const options = draft.placeOptions.includes(value)
      ? draft.placeOptions
      : [...draft.placeOptions, value];
    updateDraft('placeOptions', options);
    updateDraft('places', [...new Set([...draft.places, value])]);
    setNewPlace('');
  };

  const saveDraft = async () => {
    try {
      await AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
      setPageError('');
      setNotice('입력 정보를 이 기기에 임시 저장했어요.');
    } catch {
      setPageError('임시 저장에 실패했어요. 다시 시도해주세요.');
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
    if (!draft.pet.name || !draft.pet.species) {
      setPageError('함께 여행할 반려동물 정보를 입력해주세요.');
      return;
    }
    if (draft.places.length === 0) {
      setPageError('선호 장소를 한 개 이상 선택해주세요.');
      return;
    }

    try {
      await AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch {
      setPageError('입력 정보를 저장하지 못했어요. 다시 시도해주세요.');
      return;
    }

    setPageError('');
    router.push({
      pathname: '/routes/result',
      params: {
        petName: draft.pet.name,
        tripTitle: draft.trip.title,
        startAt: draft.trip.startAt,
        endAt: draft.trip.endAt,
        pace: draft.pace,
        selectedPlaces: draft.places.join(','),
      },
    });
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.mobileFrame}>
        <View style={styles.header}>
          <View style={styles.brandRow}>
            <View style={styles.brandIcon}>
              <Ionicons color={colors.white} name="paw" size={18} />
            </View>
            <Text style={styles.brandText}>오멍가멍</Text>
          </View>
          <View style={styles.headerActions}>
            <Pressable accessibilityLabel="알림 보기" onPress={() => setUtilityModal('notifications')}>
              <Ionicons color={colors.ink} name="notifications-outline" size={21} />
            </Pressable>
            <Pressable
              accessibilityLabel="반려동물 프로필 보기"
              onPress={() => setUtilityModal('profile')}
              style={styles.profileBadge}
            >
              <Text style={styles.profileEmoji}>🐶</Text>
            </Pressable>
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.titleArea}>
            <Text style={styles.pageTitle}>루트 추천 정보 입력</Text>
            <Text style={styles.pageDescription}>필수 정보만 입력하면 맞춤 루트를 추천해드려요.</Text>
            <View style={styles.progressRow}>
              <View style={styles.quickBadge}>
                <Ionicons color={colors.deepMint} name="flash" size={13} />
                <Text style={styles.quickBadgeText}>간단 정보 입력</Text>
              </View>
              <Text style={styles.progressText}>1 / 1</Text>
            </View>
          </View>

          <Section icon="calendar-outline" onEdit={openTripEditor} title="여행 일정">
            <View style={styles.valueBox}>
              <View style={styles.flexOne}>
                <Text style={styles.valueLabel}>{draft.trip.title}</Text>
                <Text numberOfLines={1} style={styles.valueText}>
                  {formatShortDate(draft.trip.startAt)} {formatTime(draft.trip.startAt)} 도착  ~  {formatShortDate(draft.trip.endAt)} {formatTime(draft.trip.endAt)} 출발
                </Text>
              </View>
              <Text style={styles.durationText}>
                {formatTripDuration(draft.trip.startAt, draft.trip.endAt)}
              </Text>
            </View>
          </Section>

          <Section accent={colors.deepMint} icon="car-outline" title="이동수단">
            <View style={styles.chipRow}>
              {draft.transportOptions.map((item, index) => (
                <ChoiceChip
                  key={item}
                  label={item}
                  onDelete={
                    index > 2
                      ? () => {
                          const options = draft.transportOptions.filter((option) => option !== item);
                          updateDraft('transportOptions', options);
                          if (draft.transport === item) updateDraft('transport', options[0]);
                        }
                      : undefined
                  }
                  onPress={() => updateDraft('transport', item)}
                  selected={draft.transport === item}
                />
              ))}
            </View>
            <AddRow
              onAdd={addTransport}
              onChangeText={setNewTransport}
              placeholder="다른 이동수단 입력"
              value={newTransport}
            />
          </Section>

          <Section icon="bed-outline" title="숙소">
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
                  onPress={() =>
                    Alert.alert('숙소 삭제', `${stay.name} 정보를 삭제할까요?`, [
                      { style: 'cancel', text: '취소' },
                      {
                        onPress: () => updateDraft('stays', draft.stays.filter((item) => item.id !== stay.id)),
                        style: 'destructive',
                        text: '삭제',
                      },
                    ])
                  }
                >
                  <Ionicons color={colors.red} name="trash-outline" size={17} />
                </Pressable>
              </View>
            ))}
            <Pressable onPress={() => openStayEditor()} style={styles.dashedButton}>
              <Ionicons color={colors.orange} name="add-circle" size={15} />
              <Text style={styles.dashedButtonText}>숙소 추가</Text>
            </Pressable>
          </Section>

          <Section
            accent={colors.deepMint}
            icon="paw-outline"
            onEdit={openPetEditor}
            title="반려동물 정보"
          >
            <View style={styles.petRow}>
              <View style={styles.petAvatar}>
                <Text style={styles.petEmoji}>🐶</Text>
              </View>
              <View style={styles.flexOne}>
                <Text style={styles.petName}>{draft.pet.name}</Text>
                <Text style={styles.petDescription}>
                  {draft.pet.species} · {draft.pet.size || '크기 미입력'} · {draft.pet.weight || '체중 미입력'}
                </Text>
              </View>
              <Ionicons color={colors.deepMint} name="checkmark-circle" size={18} />
            </View>
          </Section>

          <Section icon="location-outline" title="선호 장소">
            <View style={styles.chipRow}>
              {draft.placeOptions.map((item) => (
                <ChoiceChip
                  key={item}
                  label={item}
                  onDelete={
                    initialDraft.placeOptions.includes(item)
                      ? undefined
                      : () => {
                          updateDraft('placeOptions', draft.placeOptions.filter((option) => option !== item));
                          updateDraft('places', draft.places.filter((place) => place !== item));
                        }
                  }
                  onPress={() =>
                    updateDraft(
                      'places',
                      draft.places.includes(item)
                        ? draft.places.filter((place) => place !== item)
                        : [...draft.places, item],
                    )
                  }
                  selected={draft.places.includes(item)}
                />
              ))}
            </View>
            <AddRow
              onAdd={addPlace}
              onChangeText={setNewPlace}
              placeholder="원하는 장소 유형 입력"
              value={newPlace}
            />
          </Section>

          <Section accent={colors.deepMint} icon="speedometer-outline" title="여행 속도">
            <View style={styles.paceRow}>
              {['여유롭게', '적당히', '알차게'].map((item) => (
                <Pressable
                  key={item}
                  onPress={() => updateDraft('pace', item)}
                  style={[styles.paceButton, draft.pace === item && styles.paceButtonSelected]}
                >
                  <Text style={[styles.paceText, draft.pace === item && styles.paceTextSelected]}>
                    {item}
                  </Text>
                </Pressable>
              ))}
            </View>
          </Section>

          <View style={styles.summaryCard}>
            <View style={styles.summaryHeader}>
              <View>
                <Text style={styles.summaryEyebrow}>입력 정보 요약</Text>
                <Text style={styles.summaryTitle}>{draft.pet.name}와 함께하는 {draft.trip.title}</Text>
              </View>
              <Text style={styles.summaryPet}>🐶</Text>
            </View>
            <Text style={styles.summaryLine}>🚗 {draft.transport}   ·   🏡 숙소 {draft.stays.length}곳</Text>
            <Text style={styles.summaryLine}>📍 {draft.places.join(', ') || '선호 장소 미선택'}</Text>
            <Text style={styles.summaryLine}>🌿 여행 속도 {draft.pace}</Text>
          </View>

          {notice ? (
            <View accessibilityRole="alert" style={styles.notice}>
              <Ionicons color={colors.deepMint} name="checkmark-circle" size={17} />
              <Text style={styles.noticeText}>{notice}</Text>
            </View>
          ) : null}

          {pageError ? (
            <View accessibilityRole="alert" style={styles.pageErrorBox}>
              <Ionicons color={colors.red} name="alert-circle" size={17} />
              <Text style={styles.pageErrorText}>{pageError}</Text>
            </View>
          ) : null}

          <Pressable
            onPress={() => void requestRecommendation()}
            style={({ pressed }) => [styles.ctaButton, pressed && styles.pressed]}
            testID="recommend-route-button"
          >
            <Ionicons color={colors.white} name="paw" size={18} />
            <Text style={styles.ctaText}>저장하고 루트 추천받기</Text>
          </Pressable>

          <View style={styles.secondaryActions}>
            <Pressable onPress={() => void saveDraft()} style={styles.secondaryAction}>
              <Ionicons color={colors.gray} name="bookmark-outline" size={16} />
              <Text style={styles.secondaryActionText}>임시 저장</Text>
            </Pressable>
            <View style={styles.actionDivider} />
            <Pressable
              onPress={() => setUtilityModal('later')}
              style={styles.secondaryAction}
            >
              <Ionicons color={colors.gray} name="time-outline" size={16} />
              <Text style={styles.secondaryActionText}>나중에 입력하기</Text>
            </Pressable>
          </View>
        </ScrollView>

        <RouteBottomNavigation />
      </View>

      <Modal animationType="slide" onRequestClose={closeEditor} transparent visible={editTarget !== null}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalBackdrop}
        >
          <Pressable onPress={closeEditor} style={styles.modalDismissArea} />
          <View style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>
              {editTarget === 'trip' ? '여행 일정 수정' : editTarget === 'pet' ? '반려동물 정보 수정' : '숙소 정보'}
            </Text>

            {editTarget === 'trip' ? (
              <>
                <FormInput label="여행 이름" name="title" setValues={setFormValues} values={formValues} />
                <Text style={styles.formGroupTitle}>도착 일시</Text>
                <View style={styles.dateTimeRow}>
                  <DateTimeButton
                    icon="calendar-outline"
                    label={formatDate(formValues.startAt)}
                    onPress={() => setPickerTarget('start-date')}
                    selected={pickerTarget === 'start-date'}
                  />
                  <DateTimeButton
                    icon="time-outline"
                    label={formatTime(formValues.startAt)}
                    onPress={() => setPickerTarget('start-time')}
                    selected={pickerTarget === 'start-time'}
                  />
                </View>

                <Text style={styles.formGroupTitle}>출발 일시</Text>
                <View style={styles.dateTimeRow}>
                  <DateTimeButton
                    icon="calendar-outline"
                    label={formatDate(formValues.endAt)}
                    onPress={() => setPickerTarget('end-date')}
                    selected={pickerTarget === 'end-date'}
                  />
                  <DateTimeButton
                    icon="time-outline"
                    label={formatTime(formValues.endAt)}
                    onPress={() => setPickerTarget('end-time')}
                    selected={pickerTarget === 'end-time'}
                  />
                </View>

                {pickerTarget ? (
                  <View style={styles.pickerPanel}>
                    <View style={styles.pickerHeader}>
                      <Text style={styles.pickerTitle}>
                        {pickerTarget.endsWith('date') ? '날짜 선택' : '시간 선택'}
                      </Text>
                      <Pressable onPress={() => setPickerTarget(null)}>
                        <Text style={styles.pickerDoneText}>완료</Text>
                      </Pressable>
                    </View>
                    {pickerTarget.endsWith('date') ? (
                      <CalendarPicker
                        onChange={(selectedDate) => updateTripDateTime(pickerTarget, selectedDate)}
                        value={new Date(
                          pickerTarget.startsWith('start')
                            ? formValues.startAt
                            : formValues.endAt,
                        )}
                      />
                    ) : (
                      <WheelTimePicker
                        onChange={(selectedDate) => updateTripDateTime(pickerTarget, selectedDate)}
                        value={new Date(
                          pickerTarget.startsWith('start')
                            ? formValues.startAt
                            : formValues.endAt,
                        )}
                      />
                    )}
                  </View>
                ) : null}
              </>
            ) : null}

            {editTarget === 'pet' ? (
              <>
                <FormInput label="이름" name="name" setValues={setFormValues} values={formValues} />
                <FormInput label="종류" name="species" setValues={setFormValues} values={formValues} />
                <View style={styles.twoColumns}>
                  <View style={styles.column}>
                    <FormInput label="크기" name="size" setValues={setFormValues} values={formValues} />
                  </View>
                  <View style={styles.column}>
                    <FormInput label="체중" name="weight" setValues={setFormValues} values={formValues} />
                  </View>
                </View>
              </>
            ) : null}

            {editTarget === 'stay' ? (
              <>
                <FormInput label="숙소 이름" name="name" setValues={setFormValues} values={formValues} />
                <View style={styles.formField}>
                  <Text style={styles.formLabel}>숙박 일차</Text>
                  <Text style={styles.formHelper}>여행 일정 중 이 숙소에서 머무는 밤을 선택해주세요.</Text>
                  <View style={styles.stayPeriodChips}>
                    {stayNightOptions.map((option) => {
                      const selected = parseStayPeriods(formValues.period ?? '').includes(option.value);
                      return (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityState={{ selected }}
                          key={option.value}
                          onPress={() => toggleStayPeriod(option.value)}
                          style={[styles.stayPeriodChip, selected && styles.stayPeriodChipSelected]}
                        >
                          <Text style={[styles.stayPeriodChipTitle, selected && styles.stayPeriodChipTitleSelected]}>
                            {option.label}
                          </Text>
                          <Text style={[styles.stayPeriodChipDate, selected && styles.stayPeriodChipDateSelected]}>
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
                <FormInput label="주소" name="address" setValues={setFormValues} values={formValues} />
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

      <Modal
        animationType="fade"
        onRequestClose={() => setUtilityModal(null)}
        transparent
        visible={utilityModal !== null}
      >
        <View style={styles.utilityBackdrop}>
          <Pressable onPress={() => setUtilityModal(null)} style={styles.utilityDismissArea} />
          <View style={styles.utilityModalCard}>
            <View style={styles.utilityModalHeader}>
              <Text style={styles.utilityModalTitle}>
                {utilityModal === 'notifications'
                  ? '알림'
                  : utilityModal === 'profile'
                    ? '반려동물 프로필'
                    : '나중에 입력하기'}
              </Text>
              <Pressable accessibilityLabel="닫기" onPress={() => setUtilityModal(null)}>
                <Ionicons color={colors.gray} name="close" size={23} />
              </Pressable>
            </View>

            {utilityModal === 'notifications' ? (
              <View style={styles.notificationList}>
                <View style={styles.notificationItem}>
                  <View style={styles.notificationIcon}>
                    <Ionicons color={colors.orange} name="sunny-outline" size={19} />
                  </View>
                  <View style={styles.flexOne}>
                    <Text style={styles.notificationTitle}>제주 날씨를 확인했어요</Text>
                    <Text style={styles.notificationText}>여행 첫날은 맑고 산책하기 좋은 날씨예요.</Text>
                  </View>
                </View>
                <View style={styles.notificationItem}>
                  <View style={[styles.notificationIcon, styles.notificationIconMint]}>
                    <Ionicons color={colors.deepMint} name="paw-outline" size={19} />
                  </View>
                  <View style={styles.flexOne}>
                    <Text style={styles.notificationTitle}>반려동물 정보를 확인해주세요</Text>
                    <Text style={styles.notificationText}>몽이의 체중과 크기를 언제든 수정할 수 있어요.</Text>
                  </View>
                </View>
              </View>
            ) : null}

            {utilityModal === 'profile' ? (
              <View>
                <View style={styles.profileModalPet}>
                  <View style={styles.profileModalAvatar}><Text style={styles.profileModalEmoji}>🐶</Text></View>
                  <View style={styles.flexOne}>
                    <Text style={styles.profileModalName}>{draft.pet.name}</Text>
                    <Text style={styles.profileModalText}>
                      {draft.pet.species} · {draft.pet.size} · {draft.pet.weight}
                    </Text>
                  </View>
                </View>
                <Pressable
                  onPress={() => {
                    setUtilityModal(null);
                    openPetEditor();
                  }}
                  style={styles.utilityPrimaryButton}
                >
                  <Text style={styles.utilityPrimaryText}>정보 수정하기</Text>
                </Pressable>
              </View>
            ) : null}

            {utilityModal === 'later' ? (
              <View>
                <Text style={styles.laterDescription}>
                  현재 입력한 내용은 유지됩니다. 기본 정보로 바로 추천을 받거나 계속 입력할 수 있어요.
                </Text>
                <Pressable
                  onPress={() => {
                    setUtilityModal(null);
                    void requestRecommendation();
                  }}
                  style={styles.utilityPrimaryButton}
                >
                  <Text style={styles.utilityPrimaryText}>현재 정보로 추천받기</Text>
                </Pressable>
                <Pressable onPress={() => setUtilityModal(null)} style={styles.utilitySecondaryButton}>
                  <Text style={styles.utilitySecondaryText}>계속 입력하기</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function DateTimeButton({
  icon,
  label,
  onPress,
  selected,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
  selected: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.dateTimeButton, selected && styles.dateTimeButtonSelected]}
    >
      <Ionicons color={selected ? colors.orange : colors.gray} name={icon} size={17} />
      <Text numberOfLines={1} style={[styles.dateTimeText, selected && styles.dateTimeTextSelected]}>
        {label}
      </Text>
    </Pressable>
  );
}

function FormInput({
  label,
  name,
  values,
  setValues,
}: {
  label: string;
  name: string;
  values: Record<string, string>;
  setValues: React.Dispatch<React.SetStateAction<Record<string, string>>>;
}) {
  return (
    <View style={styles.formField}>
      <Text style={styles.formLabel}>{label}</Text>
      <TextInput
        onChangeText={(value) => setValues((current) => ({ ...current, [name]: value }))}
        placeholder={`${label} 입력`}
        placeholderTextColor="#A6A9AD"
        style={styles.formInput}
        value={values[name] ?? ''}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { alignItems: 'center', backgroundColor: colors.white, flex: 1 },
  mobileFrame: { backgroundColor: colors.white, flex: 1, maxWidth: 430, width: '100%' },
  header: { alignItems: 'center', backgroundColor: colors.white, flexDirection: 'row', justifyContent: 'space-between', paddingBottom: 7, paddingHorizontal: 18, paddingTop: 9 },
  brandRow: { alignItems: 'center', flexDirection: 'row', gap: 7 },
  brandIcon: { alignItems: 'center', backgroundColor: colors.orange, borderRadius: 16, height: 32, justifyContent: 'center', width: 32 },
  brandText: { color: colors.orange, fontSize: 19, fontWeight: '900', letterSpacing: -0.7 },
  headerActions: { alignItems: 'center', flexDirection: 'row', gap: 12 },
  profileBadge: { alignItems: 'center', backgroundColor: colors.cream, borderColor: '#FFE4BE', borderRadius: 17, borderWidth: 1, height: 34, justifyContent: 'center', width: 34 },
  profileEmoji: { fontSize: 18 },
  content: { backgroundColor: colors.white, paddingBottom: 28, paddingHorizontal: 15, paddingTop: 10 },
  titleArea: { marginBottom: 10 },
  pageTitle: { color: '#25272A', fontSize: 27, fontWeight: '900', letterSpacing: -1.1 },
  pageDescription: { color: colors.gray, fontSize: 11, marginTop: 5 },
  progressRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 11 },
  quickBadge: { alignItems: 'center', backgroundColor: '#E7F7EF', borderRadius: 999, flexDirection: 'row', gap: 4, paddingHorizontal: 10, paddingVertical: 5 },
  quickBadgeText: { color: colors.deepMint, fontSize: 11, fontWeight: '800' },
  progressText: { color: colors.ink, fontSize: 12, fontWeight: '800' },
  sectionCard: { backgroundColor: colors.white, borderColor: '#F0ECE6', borderRadius: 13, borderWidth: 1, elevation: 2, marginBottom: 8, padding: 11, shadowColor: '#8A6843', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.09, shadowRadius: 8 },
  sectionHeading: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  sectionTitleWrap: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  sectionIcon: { alignItems: 'center', borderRadius: 8, height: 27, justifyContent: 'center', width: 27 },
  sectionTitle: { color: colors.ink, fontSize: 14, fontWeight: '900' },
  editButton: { alignItems: 'center', flexDirection: 'row', gap: 3, padding: 5 },
  editText: { color: colors.gray, fontSize: 10, fontWeight: '600' },
  valueBox: { alignItems: 'center', backgroundColor: '#FFFEFC', borderColor: '#F1EDE7', borderRadius: 8, borderWidth: 1, flexDirection: 'row', paddingHorizontal: 10, paddingVertical: 8 },
  flexOne: { flex: 1 },
  valueLabel: { color: colors.ink, fontSize: 11, fontWeight: '800' },
  valueText: { color: colors.gray, fontSize: 9, marginTop: 4 },
  durationText: { color: colors.deepMint, fontSize: 11, fontWeight: '800' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  choiceChip: { alignItems: 'center', backgroundColor: '#FAF9F7', borderColor: '#ECE8E2', borderRadius: 8, borderWidth: 1, flexDirection: 'row', gap: 4, paddingHorizontal: 11, paddingVertical: 7 },
  choiceChipSelected: { backgroundColor: colors.orange, borderColor: colors.orange },
  choiceChipText: { color: colors.gray, fontSize: 10, fontWeight: '700' },
  choiceChipTextSelected: { color: colors.white },
  addRow: { alignItems: 'center', borderColor: '#D5EBE5', borderRadius: 8, borderStyle: 'dashed', borderWidth: 1, flexDirection: 'row', marginTop: 8, paddingLeft: 10 },
  addInput: { color: colors.ink, flex: 1, fontSize: 11, minHeight: 38, outlineStyle: 'none' } as never,
  inlineAddButton: { alignItems: 'center', backgroundColor: colors.deepMint, borderRadius: 7, height: 30, justifyContent: 'center', marginRight: 4, width: 34 },
  stayRow: { alignItems: 'center', backgroundColor: '#FFFEFC', borderColor: '#F1EDE7', borderRadius: 8, borderWidth: 1, flexDirection: 'row', gap: 8, marginBottom: 6, padding: 8 },
  stayDayBadge: { backgroundColor: '#FFF0DE', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 5 },
  stayDayText: { color: colors.orange, fontSize: 8, fontWeight: '800' },
  stayCopy: { flex: 1 },
  dashedButton: { alignItems: 'center', borderColor: '#FFD3A5', borderRadius: 8, borderStyle: 'dashed', borderWidth: 1, flexDirection: 'row', gap: 4, justifyContent: 'center', minHeight: 31 },
  dashedButtonText: { color: colors.orange, fontSize: 10, fontWeight: '800' },
  petRow: { alignItems: 'center', backgroundColor: '#FFFEFC', borderColor: '#F1EDE7', borderRadius: 8, borderWidth: 1, flexDirection: 'row', gap: 9, padding: 8 },
  petAvatar: { alignItems: 'center', backgroundColor: colors.cream, borderRadius: 22, height: 44, justifyContent: 'center', width: 44 },
  petEmoji: { fontSize: 25 },
  petName: { color: colors.ink, fontSize: 12, fontWeight: '800' },
  petDescription: { color: colors.gray, fontSize: 9, marginTop: 3 },
  paceRow: { flexDirection: 'row', gap: 7 },
  paceButton: { alignItems: 'center', borderColor: '#E8E4DE', borderRadius: 8, borderWidth: 1, flex: 1, paddingVertical: 8 },
  paceButtonSelected: { backgroundColor: '#EEFAF7', borderColor: colors.mint, borderWidth: 1.5 },
  paceText: { color: colors.gray, fontSize: 10, fontWeight: '700' },
  paceTextSelected: { color: colors.deepMint },
  summaryCard: { backgroundColor: '#EFF9F4', borderColor: '#CDE8DE', borderRadius: 13, borderWidth: 1, marginTop: 1, padding: 12 },
  summaryHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  summaryEyebrow: { color: colors.deepMint, fontSize: 10, fontWeight: '800' },
  summaryTitle: { color: colors.ink, fontSize: 13, fontWeight: '800', marginTop: 3 },
  summaryPet: { fontSize: 34 },
  summaryLine: { color: '#4F6E67', fontSize: 9, fontWeight: '600', marginTop: 6 },
  notice: { alignItems: 'center', backgroundColor: '#EAF8F4', borderRadius: 10, flexDirection: 'row', gap: 6, marginTop: 10, padding: 10 },
  noticeText: { color: colors.deepMint, flex: 1, fontSize: 10, fontWeight: '700' },
  pageErrorBox: { alignItems: 'center', backgroundColor: '#FFF0F0', borderRadius: 10, flexDirection: 'row', gap: 6, marginTop: 10, padding: 10 },
  pageErrorText: { color: colors.red, flex: 1, fontSize: 10, fontWeight: '700' },
  ctaButton: { alignItems: 'center', backgroundColor: colors.orange, borderRadius: 9, elevation: 3, flexDirection: 'row', gap: 7, justifyContent: 'center', marginTop: 10, minHeight: 47, shadowColor: colors.orange, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.2, shadowRadius: 8 },
  ctaText: { color: colors.white, fontSize: 14, fontWeight: '900' },
  secondaryActions: { alignItems: 'center', borderColor: colors.line, borderRadius: 11, borderWidth: 1, flexDirection: 'row', marginTop: 9, minHeight: 44 },
  secondaryAction: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: 5, justifyContent: 'center' },
  secondaryActionText: { color: colors.gray, fontSize: 10, fontWeight: '700' },
  actionDivider: { backgroundColor: colors.line, height: 20, width: 1 },
  modalBackdrop: { backgroundColor: '#00000055', flex: 1, justifyContent: 'flex-end' },
  modalDismissArea: { flex: 1 },
  modalSheet: { alignSelf: 'center', backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, maxWidth: 430, padding: 20, width: '100%' },
  modalHandle: { alignSelf: 'center', backgroundColor: '#D7D9DC', borderRadius: 2, height: 4, marginBottom: 16, width: 42 },
  modalTitle: { color: colors.ink, fontSize: 19, fontWeight: '900', marginBottom: 14 },
  formField: { marginBottom: 11 },
  formLabel: { color: colors.ink, fontSize: 11, fontWeight: '800', marginBottom: 6 },
  formHelper: { color: colors.gray, fontSize: 9, marginBottom: 9, marginTop: -2 },
  formInput: { borderColor: colors.line, borderRadius: 10, borderWidth: 1, color: colors.ink, fontSize: 12, minHeight: 44, outlineStyle: 'none', paddingHorizontal: 12 } as never,
  stayPeriodChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  stayPeriodChip: { backgroundColor: '#FAF9F7', borderColor: '#E8E4DE', borderRadius: 10, borderWidth: 1, minWidth: 104, paddingHorizontal: 11, paddingVertical: 9 },
  stayPeriodChipSelected: { backgroundColor: '#FFF4E7', borderColor: colors.orange, borderWidth: 1.5 },
  stayPeriodChipTitle: { color: colors.gray, fontSize: 11, fontWeight: '900' },
  stayPeriodChipTitleSelected: { color: colors.orange },
  stayPeriodChipDate: { color: '#A3A7AC', fontSize: 8, fontWeight: '600', marginTop: 3 },
  stayPeriodChipDateSelected: { color: '#C85F00' },
  emptyStayPeriod: { backgroundColor: colors.lightGray, borderRadius: 9, color: colors.gray, fontSize: 10, padding: 11 },
  formGroupTitle: { color: colors.ink, fontSize: 11, fontWeight: '800', marginBottom: 7, marginTop: 2 },
  dateTimeRow: { flexDirection: 'row', gap: 8, marginBottom: 13 },
  dateTimeButton: { alignItems: 'center', borderColor: colors.line, borderRadius: 10, borderWidth: 1, flex: 1, flexDirection: 'row', gap: 6, minHeight: 44, paddingHorizontal: 10 },
  dateTimeButtonSelected: { backgroundColor: '#FFF7ED', borderColor: colors.orange },
  dateTimeText: { color: colors.gray, flexShrink: 1, fontSize: 10, fontWeight: '700' },
  dateTimeTextSelected: { color: colors.orange },
  pickerPanel: { backgroundColor: '#FAFAFA', borderColor: colors.line, borderRadius: 13, borderWidth: 1, marginBottom: 12, overflow: 'hidden', padding: 10 },
  pickerHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingBottom: 6 },
  pickerTitle: { color: colors.ink, fontSize: 12, fontWeight: '800' },
  pickerDoneText: { color: colors.orange, fontSize: 12, fontWeight: '900' },
  twoColumns: { flexDirection: 'row', gap: 9 },
  column: { flex: 1 },
  modalActions: { flexDirection: 'row', gap: 9, marginTop: 8 },
  cancelButton: { alignItems: 'center', borderColor: colors.line, borderRadius: 11, borderWidth: 1, flex: 1, justifyContent: 'center', minHeight: 46 },
  cancelText: { color: colors.gray, fontSize: 13, fontWeight: '800' },
  saveButton: { alignItems: 'center', backgroundColor: colors.orange, borderRadius: 11, flex: 1.4, justifyContent: 'center', minHeight: 46 },
  saveText: { color: colors.white, fontSize: 13, fontWeight: '900' },
  formErrorBox: { alignItems: 'center', backgroundColor: '#FFF0F0', borderRadius: 9, flexDirection: 'row', gap: 6, marginBottom: 4, padding: 9 },
  formErrorText: { color: colors.red, flex: 1, fontSize: 10, fontWeight: '700' },
  utilityBackdrop: { alignItems: 'center', backgroundColor: '#00000066', flex: 1, justifyContent: 'center', padding: 18 },
  utilityDismissArea: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  utilityModalCard: { backgroundColor: colors.white, borderRadius: 20, maxWidth: 398, padding: 18, width: '100%' },
  utilityModalHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  utilityModalTitle: { color: colors.ink, fontSize: 18, fontWeight: '900' },
  notificationList: { gap: 9 },
  notificationItem: { alignItems: 'center', backgroundColor: '#FAFAFA', borderColor: colors.line, borderRadius: 12, borderWidth: 1, flexDirection: 'row', gap: 10, padding: 11 },
  notificationIcon: { alignItems: 'center', backgroundColor: '#FFF0DE', borderRadius: 19, height: 38, justifyContent: 'center', width: 38 },
  notificationIconMint: { backgroundColor: '#EAF8F4' },
  notificationTitle: { color: colors.ink, fontSize: 11, fontWeight: '800' },
  notificationText: { color: colors.gray, fontSize: 9, lineHeight: 14, marginTop: 3 },
  profileModalPet: { alignItems: 'center', backgroundColor: '#FFF9F1', borderRadius: 14, flexDirection: 'row', gap: 11, marginBottom: 13, padding: 13 },
  profileModalAvatar: { alignItems: 'center', backgroundColor: '#FFE5C3', borderRadius: 26, height: 52, justifyContent: 'center', width: 52 },
  profileModalEmoji: { fontSize: 29 },
  profileModalName: { color: colors.ink, fontSize: 15, fontWeight: '900' },
  profileModalText: { color: colors.gray, fontSize: 10, marginTop: 4 },
  laterDescription: { color: colors.gray, fontSize: 11, lineHeight: 18, marginBottom: 15 },
  utilityPrimaryButton: { alignItems: 'center', backgroundColor: colors.orange, borderRadius: 11, justifyContent: 'center', minHeight: 46 },
  utilityPrimaryText: { color: colors.white, fontSize: 12, fontWeight: '900' },
  utilitySecondaryButton: { alignItems: 'center', borderColor: colors.line, borderRadius: 11, borderWidth: 1, justifyContent: 'center', marginTop: 8, minHeight: 44 },
  utilitySecondaryText: { color: colors.gray, fontSize: 11, fontWeight: '800' },
  pressed: { opacity: 0.72 },
});

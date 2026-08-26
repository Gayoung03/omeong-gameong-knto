import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors, radius, spacing, typography } from '@/src/theme';

import { TripDeleteConfirmModal } from '../components/TripDeleteConfirmModal';
import { TripInfoEditForm } from '../components/TripInfoEditForm';
import { TripInfoRow } from '../components/TripInfoRow';
import { TripMemoEditModal } from '../components/TripMemoEditModal';
import { useDeleteTrip } from '../hooks/useDeleteTrip';
import { useTripInfoForm } from '../hooks/useTripInfoForm';
import { useTrip } from '../hooks/useTrips';
import type { Trip } from '../types/trip';
import { formatPets, formatTripPeriod, getTransportLabel } from '../utils/tripFormat';

type TripInfoScreenProps = {
  tripId: string;
};

export function TripInfoScreen({ tripId }: TripInfoScreenProps) {
  const { data: trip, isLoading, isError, refetch } = useTrip(tripId);

  if (isLoading) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <TripInfoHeader />
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (isError || !trip) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <TripInfoHeader />
        <ErrorState onRetry={() => refetch()} />
      </SafeAreaView>
    );
  }

  return <TripInfoContent trip={trip} />;
}

type TripInfoHeaderProps = {
  rightSlot?: React.ReactNode;
  leftSlot?: React.ReactNode;
};

function TripInfoHeader({ leftSlot, rightSlot }: TripInfoHeaderProps) {
  const router = useRouter();

  return (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        {leftSlot ?? (
          <Pressable
            accessibilityLabel="뒤로 가기"
            accessibilityRole="button"
            hitSlop={spacing.sm}
            onPress={() => router.back()}
          >
            <Ionicons color={colors.basalt} name="chevron-back" size={22} />
          </Pressable>
        )}
      </View>

      <Text style={styles.headerTitle}>여행 정보</Text>

      <View style={styles.headerRight}>{rightSlot}</View>
    </View>
  );
}

type TripInfoContentProps = {
  trip: Trip;
};

function TripInfoContent({ trip }: TripInfoContentProps) {
  // 화면이 보여주는 여행은 useTrip 이 들고 있다. 저장에 성공하면 캐시가 버려지고
  // 서버 값으로 다시 그려진다 — 훅이 사본을 들고 있으면 둘이 어긋난다.
  const router = useRouter();
  const form = useTripInfoForm(trip);
  const {
    isEditing,
    canSubmit,
    isSaving,
    errorMessage,
    startEditing,
    cancelEditing,
    submit,
    saveMemoOnly,
  } = form;

  const deleteMutation = useDeleteTrip();
  const [isDeleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string>();

  const confirmDelete = () => {
    deleteMutation.mutate(trip.id, {
      onError: (error) => {
        setDeleteModalOpen(false);
        setDeleteErrorMessage(getApiErrorMessage(error).description);
      },
      // 뒤로 가면 방금 지운 여행의 상세로 돌아간다. 목록으로 갈아끼운다.
      onSuccess: () => router.replace('/trips'),
    });
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <TripInfoHeader
        leftSlot={
          isEditing ? (
            <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={cancelEditing}>
              <Text style={styles.headerActionText}>취소</Text>
            </Pressable>
          ) : undefined
        }
        rightSlot={
          isEditing ? (
            <Pressable
              accessibilityRole="button"
              disabled={!canSubmit}
              hitSlop={spacing.sm}
              onPress={submit}
            >
              <Text style={[styles.headerSubmitText, !canSubmit && styles.disabledText]}>
                {isSaving ? '저장 중' : '완료'}
              </Text>
            </Pressable>
          ) : (
            <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={startEditing}>
              <Text style={styles.headerActionText}>편집</Text>
            </Pressable>
          )
        }
      />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.hero}>
          <View style={styles.avatar}>
            <Text style={styles.avatarEmoji}>{trip.coverEmoji}</Text>
          </View>
          {!isEditing && (
            <>
              <Text style={styles.tripTitle}>{trip.title}</Text>
              <Text style={styles.tripPeriod}>{formatTripPeriod(trip)}</Text>
            </>
          )}
        </View>

        {isEditing ? <TripInfoEditForm form={form} /> : <TripInfoView trip={trip} />}

        {errorMessage && <Text style={styles.saveError}>{errorMessage}</Text>}

        {/* 되돌릴 수 없는 동작이라 시각적 무게를 낮춘다. 맨 아래 회색 작은 글씨. */}
        {!isEditing && (
          <>
            <Pressable
              accessibilityRole="button"
              hitSlop={spacing.sm}
              onPress={() => setDeleteModalOpen(true)}
              style={({ pressed }) => [styles.deleteRow, pressed && styles.pressed]}
            >
              <Text style={styles.deleteText}>여행 삭제</Text>
            </Pressable>
            {deleteErrorMessage && <Text style={styles.saveError}>{deleteErrorMessage}</Text>}
          </>
        )}
      </ScrollView>

      {!isEditing && <MemoCard memo={trip.memo} onSaveMemo={saveMemoOnly} />}

      <TripDeleteConfirmModal
        isDeleting={deleteMutation.isPending}
        onCancel={() => setDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        tripTitle={trip.title}
        visible={isDeleteModalOpen}
      />
    </SafeAreaView>
  );
}

function TripInfoView({ trip }: { trip: Trip }) {
  return (
    <View style={styles.infoCard}>
      <TripInfoRow
        iconBackgroundColor={colors.primarySoft}
        iconColor={colors.primary}
        iconName="car-outline"
        isFirst
        label="이동 수단"
      >
        <Text style={styles.valueText}>{getTransportLabel(trip.transport)}</Text>
      </TripInfoRow>

      <TripInfoRow
        iconBackgroundColor={colors.leafSoft}
        iconColor={colors.leaf}
        iconName="paw-outline"
        isFirst={false}
        label="반려동물"
      >
        <Text style={styles.valueText}>{formatPets(trip.pets)}</Text>
      </TripInfoRow>

      <TripInfoRow
        iconBackgroundColor={colors.seaSoft}
        iconColor={colors.sea}
        iconName="home-outline"
        isFirst={false}
        label="숙소"
      >
        <Text style={styles.valueText}>{trip.accommodationSummary}</Text>
      </TripInfoRow>

      <TripInfoRow
        iconBackgroundColor={colors.basaltSoft}
        iconColor={colors.basalt}
        iconName="leaf-outline"
        isFirst={false}
        label="여행 스타일"
      >
        <Text style={styles.valueText}>{trip.travelStyle}</Text>
      </TripInfoRow>

      <TripInfoRow
        iconBackgroundColor={colors.primarySoft}
        iconColor={colors.primary}
        iconName="bookmark-outline"
        isFirst={false}
        label="선호 키워드"
      >
        <View style={styles.keywordRow}>
          {trip.styleKeywords.map((keyword) => (
            <View key={keyword} style={styles.keywordChip}>
              <Text style={styles.keywordText}>{keyword}</Text>
            </View>
          ))}
        </View>
      </TripInfoRow>
    </View>
  );
}

type MemoCardProps = {
  memo: string;
  onSaveMemo: (memo: string) => void;
};

function MemoCard({ memo, onSaveMemo }: MemoCardProps) {
  const [isModalOpen, setModalOpen] = useState(false);

  const handleSubmit = (nextMemo: string) => {
    onSaveMemo(nextMemo);
    setModalOpen(false);
  };

  return (
    <>
      <View style={styles.memoCard}>
        <View style={styles.memoHeader}>
          <Text style={styles.memoLabel}>메모</Text>
          <Pressable
            accessibilityRole="button"
            hitSlop={spacing.sm}
            onPress={() => setModalOpen(true)}
          >
            <Text style={styles.memoEditText}>{memo.length === 0 ? '작성' : '편집'}</Text>
          </Pressable>
        </View>

        {memo.length === 0 ? (
          <Text style={styles.memoEmpty}>이번 여행에서 기억해둘 점을 남겨보세요</Text>
        ) : (
          <Text numberOfLines={3} style={styles.memoText}>
            {memo}
          </Text>
        )}
      </View>

      {isModalOpen && (
        <TripMemoEditModal
          initialMemo={memo}
          onClose={() => setModalOpen(false)}
          onSubmit={handleSubmit}
        />
      )}
    </>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    height: 56,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  headerLeft: {
    left: spacing.md,
    position: 'absolute',
  },
  headerRight: {
    position: 'absolute',
    right: spacing.md,
  },
  headerTitle: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
    includeFontPadding: false,
    lineHeight: 24,
  },
  headerActionText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  headerSubmitText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  disabledText: {
    color: colors.textTertiary,
  },
  scrollContent: {
    paddingBottom: spacing.xl,
  },
  hero: {
    alignItems: 'center',
    gap: spacing.xs + 1,
    paddingBottom: spacing.sm,
    paddingTop: spacing.md,
  },
  avatar: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 84,
    justifyContent: 'center',
    width: 84,
  },
  avatarEmoji: {
    fontSize: 44,
  },
  tripTitle: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize + 1,
    fontWeight: '700',
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  tripPeriod: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
  },
  infoCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg + 2,
    borderWidth: 1,
    marginHorizontal: spacing.lg - 2,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  valueText: {
    color: colors.basalt,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  keywordRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  keywordChip: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
  },
  keywordText: {
    color: colors.primary,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  memoCard: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.lg,
    gap: spacing.xs + 1,
    marginBottom: spacing.md,
    marginHorizontal: spacing.lg - 2,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 4,
  },
  memoHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  memoLabel: {
    color: colors.primary,
    fontSize: typography.micro.fontSize + 1,
    fontWeight: '700',
  },
  memoEditText: {
    color: colors.primary,
    fontSize: typography.micro.fontSize + 1,
    fontWeight: '700',
  },
  memoText: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    lineHeight: 22,
  },
  memoEmpty: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
  },
  deleteRow: {
    alignItems: 'center',
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
  },
  deleteText: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
    textDecorationLine: 'underline',
  },
  pressed: {
    opacity: 0.6,
  },
  saveError: {
    color: colors.error,
    fontSize: typography.label.fontSize,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.lg,
    textAlign: 'center',
  },
});

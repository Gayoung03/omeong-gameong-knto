import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { AppHeader } from '@/src/components/layout/AppHeader';
import { ScreenTitleBar } from '@/src/components/layout/ScreenTitleBar';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors, radius, spacing, typography } from '@/src/theme';

import { TripDeleteConfirmModal } from '../components/TripDeleteConfirmModal';
import { TripListCard } from '../components/TripListCard';
import { useDeleteTrip } from '../hooks/useDeleteTrip';
import { useTrips } from '../hooks/useTrips';
import type { TripListItem } from '../types/trip';

export function MyTripsScreen() {
  const router = useRouter();
  const { data: trips, error, isLoading, isError, refetch } = useTrips();
  const deleteMutation = useDeleteTrip();
  const [pendingDeleteTrip, setPendingDeleteTrip] = useState<TripListItem | null>(null);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState('');

  const openTrip = (tripId: string) => {
    router.push({ pathname: '/trips/[tripId]', params: { tripId } });
  };

  /**
   * 여행은 코스 추천으로 만든다.
   * TODO: 추천 결과 저장이 내 여행으로 연결되면 저장 후 이 목록으로 돌아오게 한다.
   */
  const startNewTrip = () => {
    router.push('/routes');
  };

  const confirmDelete = () => {
    if (!pendingDeleteTrip) return;
    deleteMutation.mutate(pendingDeleteTrip.id, {
      onError: (deleteError) => {
        setPendingDeleteTrip(null);
        setDeleteErrorMessage(getApiErrorMessage(deleteError).description);
      },
      onSuccess: () => {
        setPendingDeleteTrip(null);
        setDeleteErrorMessage('');
      },
    });
  };

  const renderBody = () => {
    if (isLoading) {
      return (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateDescription}>여행 목록을 불러오는 중이에요</Text>
        </View>
      );
    }

    if (isError) {
      return (
        <ErrorState
          error={error}
          onRetry={() => void refetch()}
          title="여행 목록을 불러오지 못했어요"
        />
      );
    }

    if (!trips || trips.length === 0) {
      return (
        <View style={styles.centered}>
          <Text style={styles.stateTitle}>저장한 여행이 없어요</Text>
          <Text style={styles.stateDescription}>
            코스 추천으로 첫 여행을 만들어보세요.
          </Text>
          <Pressable onPress={startNewTrip} style={styles.createButton}>
            <Text style={styles.createButtonText}>＋ 새 여행 만들기</Text>
          </Pressable>
        </View>
      );
    }

    return (
      <FlatList
        contentContainerStyle={styles.listContent}
        data={trips}
        keyExtractor={(trip) => trip.id}
        renderItem={({ item }) => (
          <TripListCard
            isDeleting={deleteMutation.isPending && pendingDeleteTrip?.id === item.id}
            onDelete={() => {
              setDeleteErrorMessage('');
              setPendingDeleteTrip(item);
            }}
            onPress={() => openTrip(item.id)}
            trip={item}
          />
        )}
        showsVerticalScrollIndicator={false}
      />
    );
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <AppHeader notifications="popup" />
      <ScreenTitleBar
        right={
          /* 여행 기록의 '새로운 순간 남기기' 와 같은 헤더 pill 스타일을 쓴다. */
          <Pressable
            accessibilityLabel="여행 추가"
            accessibilityRole="button"
            onPress={startNewTrip}
            style={({ pressed }) => [styles.addButton, pressed && styles.addButtonPressed]}
          >
            <Ionicons color={colors.primary} name="add" size={18} />
            <Text style={styles.addButtonLabel}>여행 추가</Text>
          </Pressable>
        }
        title="내 여행"
      />
      {deleteErrorMessage ? <Text style={styles.deleteError}>{deleteErrorMessage}</Text> : null}
      {renderBody()}
      <TripDeleteConfirmModal
        isDeleting={deleteMutation.isPending}
        onCancel={() => setPendingDeleteTrip(null)}
        onConfirm={confirmDelete}
        tripTitle={pendingDeleteTrip?.title ?? '여행 삭제'}
        visible={Boolean(pendingDeleteTrip)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  addButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    height: 40,
    justifyContent: 'center',
    paddingHorizontal: spacing.md - 2,
  },
  addButtonLabel: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: '600',
  },
  addButtonPressed: {
    opacity: 0.7,
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  createButton: {
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    marginTop: spacing.xs,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm + 2,
  },
  createButtonText: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  deleteError: {
    backgroundColor: colors.errorBg,
    color: colors.error,
    fontSize: typography.caption.fontSize,
    marginHorizontal: spacing.md,
    padding: spacing.sm,
    textAlign: 'center',
  },
  listContent: {
    gap: spacing.sm,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  stateDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    textAlign: 'center',
  },
  stateTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
});

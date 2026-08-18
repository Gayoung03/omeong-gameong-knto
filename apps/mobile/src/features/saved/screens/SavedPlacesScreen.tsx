import { router } from 'expo-router';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { SavedPlaceCard } from '../components/SavedPlaceCard';
import { useRemoveSavedPlace, useSavedPlaces } from '../hooks/useSavedPlaces';

export function SavedPlacesScreen() {
  const { data: places = [], isPending } = useSavedPlaces();
  const removePlace = useRemoveSavedPlace();

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="저장한 장소" />

      {isPending ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : places.length === 0 ? (
        <EmptyState
          actionLabel="장소 탐색으로 가기"
          description="장소 탐색에서 하트를 누르면 여기에 모입니다."
          icon="bookmark-outline"
          onPressAction={() => router.push('/place-explorer')}
          title="아직 저장한 장소가 없어요"
        />
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.list}>
            {places.map((place) => (
              <SavedPlaceCard
                key={place.id}
                onPressRemove={() => removePlace.mutate(place.id)}
                place={place}
              />
            ))}
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  list: {
    gap: spacing.sm,
  },
  loading: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});

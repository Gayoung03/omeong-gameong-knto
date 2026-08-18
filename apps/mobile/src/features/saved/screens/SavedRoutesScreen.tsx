import { router } from 'expo-router';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { SavedRouteCard } from '../components/SavedRouteCard';
import { useRemoveSavedRoute, useSavedRoutes } from '../hooks/useSavedRoutes';

/**
 * 내부 용어는 `route`(가이드 11장), 화면 문구만 "코스"로 둔다.
 */
export function SavedRoutesScreen() {
  const { data: routes = [], isPending } = useSavedRoutes();
  const removeRoute = useRemoveSavedRoute();

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="저장한 코스" />

      {isPending ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : routes.length === 0 ? (
        <EmptyState
          actionLabel="루트 추천받기"
          description="루트 추천에서 마음에 드는 코스를 저장하면 여기에 모입니다."
          icon="map-outline"
          onPressAction={() => router.push('/routes')}
          title="아직 저장한 코스가 없어요"
        />
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.list}>
            {routes.map((route) => (
              <SavedRouteCard
                key={route.id}
                onPressRemove={() => removeRoute.mutate(route.id)}
                route={route}
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

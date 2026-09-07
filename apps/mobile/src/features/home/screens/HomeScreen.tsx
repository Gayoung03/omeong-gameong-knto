import { router } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';

import { AppHeader } from '@/src/components/layout/AppHeader';
import { useUserProfile } from '@/src/features/profile/hooks/useUserProfile';
import { useTrips } from '@/src/features/trips/hooks/useTrips';
import { colors, spacing } from '@/src/theme';

import { ContentRecommendation } from '../components/ContentRecommendation';
import { QuickMenu } from '../components/QuickMenu';
import { RegionalRecommendation } from '../components/RegionalRecommendation';
import { WeatherHero } from '../components/WeatherHero';
import { fetchEditorialStories } from '../api/editorialApi';
import { fetchJejuWeather } from '../api/weatherApi';
import { quickMenuItems } from '../constants/quickMenu';
import type { EditorialStory, QuickMenuItem } from '../types/home';
import type { PlaceRegion } from '@/src/features/places/types/place';

export function HomeScreen() {
  const [openedAt] = useState(Date.now);
  const { data: user } = useUserProfile();
  const { data: trips = [] } = useTrips();
  const weather = useQuery({
    queryKey: ['home', 'weather'],
    queryFn: fetchJejuWeather,
    staleTime: 10 * 60 * 1000,
  });
  const editorial = useQuery({
    queryKey: ['home', 'editorial-stories'],
    queryFn: fetchEditorialStories,
    staleTime: 5 * 60 * 1000,
  });
  const openPlaceExplorer = (region?: PlaceRegion) => {
    router.push({
      pathname: '/place-explorer',
      params: region ? { region } : {},
    });
  };

  const handleQuickMenuPress = (item: QuickMenuItem) => {
    if (item.destination === 'chatbot') {
      router.push('/chatbot');
      return;
    }

    if (item.destination === 'place-explorer') {
      openPlaceExplorer();
      return;
    }

    if (item.destination === 'travel-preparation') {
      router.push('/travel-guides/preparation');
      return;
    }

    if (item.destination === 'travel-log-new') {
      router.push('/travel-logs/new-moment');
      return;
    }

    if (item.destination === 'saved-places') {
      router.push('/saved/places');
    }
  };

  const openStory = (story: EditorialStory) => {
    router.push(`/stories/${story.id}`);
  };
  const hasUpcomingTrip = trips.some((trip) => new Date(trip.startAt).getTime() > openedAt);

  return (
    <SafeAreaView style={styles.safeArea}>
      <AppHeader />
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <WeatherHero
          error={weather.isError}
          loading={weather.isPending}
          nickname={user?.nickname}
          onPressChatbot={() => router.push('/chatbot')}
          onRetry={() => weather.refetch()}
          weather={weather.data ?? []}
        />

        <View style={styles.section}>
          <QuickMenu items={quickMenuItems} onPressItem={handleQuickMenuPress} />
        </View>

        <View style={styles.section}>
          <RegionalRecommendation
            onPressRegion={openPlaceExplorer}
            onPressViewAll={() => openPlaceExplorer()}
          />
        </View>

        <View style={styles.section}>
          <ContentRecommendation
            onPressPreparation={() => router.push('/travel-guides/preparation')}
            onPressStory={openStory}
            showPreparation={hasUpcomingTrip}
            stories={editorial.data ?? []}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  scrollContent: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
    paddingTop: spacing.md,
  },
  section: {
    marginTop: spacing.lg,
  },
});

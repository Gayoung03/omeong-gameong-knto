import { router } from 'expo-router';
import { SafeAreaView, ScrollView, StyleSheet, View } from 'react-native';

import { AppHeader } from '@/src/components/layout/AppHeader';
import { colors, spacing } from '@/src/theme';

import { ContentRecommendation } from '../components/ContentRecommendation';
import { QuickMenu } from '../components/QuickMenu';
import { RegionalRecommendation } from '../components/RegionalRecommendation';
import { WeatherHero } from '../components/WeatherHero';
import { mockEditorialCards, mockWeather, quickMenuItems } from '../data/homeMockData';
import type { QuickMenuItem } from '../types/home';
import type { PlaceRegion } from '@/src/features/places/types/place';

export function HomeScreen() {
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

    router.push({ pathname: '/coming-soon', params: { title: item.title } });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <AppHeader />
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <WeatherHero onPressChatbot={() => router.push('/chatbot')} weather={mockWeather} />

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
          <ContentRecommendation cards={mockEditorialCards} />
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
    paddingBottom: 96,
  },
  section: {
    marginTop: 25,
  },
});

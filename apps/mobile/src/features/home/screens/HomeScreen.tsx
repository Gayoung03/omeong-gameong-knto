import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';

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
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.brandHeader}>
          <View style={styles.brand}>
            <View style={styles.brandIcon}>
              <Ionicons color={colors.surface} name="paw" size={17} />
            </View>
            <Text style={styles.brandText}>오멍가멍</Text>
          </View>
          <View style={styles.headerActions}>
            <Pressable accessibilityLabel="알림" hitSlop={10}>
              <Ionicons color={colors.textPrimary} name="notifications-outline" size={23} />
            </Pressable>
            <View style={styles.profileCircle}>
              <Ionicons color={colors.primary} name="paw" size={16} />
            </View>
          </View>
        </View>

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
  brandHeader: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  brandIcon: {
    width: 29,
    height: 29,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
  },
  brandText: {
    color: colors.primary,
    fontSize: 19,
    fontWeight: '900',
    letterSpacing: -0.8,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
  },
  profileCircle: {
    width: 31,
    height: 31,
    borderWidth: 1,
    borderColor: '#F0E5DF',
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF8F3',
  },
  section: {
    marginTop: 25,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import {
  Image,
  ImageBackground,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { NativeScrollEvent, NativeSyntheticEvent } from 'react-native';

import { brandAssets } from '@/src/config/brandAssets';
import { colors, overlayColors, radius, spacing } from '@/src/theme';

import type { WeatherSummary } from '../types/home';

const WEATHER_BACKGROUND = require('@/assets/images/home-weather-background.png');

type WeatherHeroProps = {
  weather: WeatherSummary[];
  nickname?: string;
  loading: boolean;
  error: boolean;
  onPressChatbot: () => void;
  onRetry: () => void;
};

export function WeatherHero({
  weather,
  nickname,
  loading,
  error,
  onPressChatbot,
  onRetry,
}: WeatherHeroProps) {
  const [width, setWidth] = useState(0);
  const [page, setPage] = useState(0);

  const handleScrollEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (width) setPage(Math.round(event.nativeEvent.contentOffset.x / width));
  };

  return (
    <View style={styles.card}>
      <View
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
        style={styles.carousel}
      >
        {loading || error ? (
          <View style={styles.stateArea}>
            <Ionicons color={colors.seaDeep} name="partly-sunny-outline" size={28} />
            <Text style={styles.stateText}>
              {loading ? '제주 날씨를 불러오는 중이에요.' : '날씨를 불러오지 못했어요.'}
            </Text>
            {error && (
              <Pressable accessibilityRole="button" onPress={onRetry} style={styles.retryButton}>
                <Text style={styles.retryText}>다시 시도</Text>
              </Pressable>
            )}
          </View>
        ) : (
          <>
            <ScrollView
              decelerationRate="fast"
              horizontal
              onMomentumScrollEnd={handleScrollEnd}
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              snapToInterval={width || undefined}
            >
              {weather.map((item) => (
                <ImageBackground
                  imageStyle={styles.image}
                  key={item.location}
                  source={WEATHER_BACKGROUND}
                  style={[styles.imageArea, { width }]}
                >
                  <View style={styles.scrim} />
                  <Image
                    accessibilityLabel="달리는 혼디 강아지 캐릭터"
                    resizeMode="contain"
                    source={brandAssets.character.running}
                    style={styles.heroCharacter}
                  />
                  <View style={styles.weatherCopy}>
                    <Text style={styles.greeting}>안녕, {nickname ?? '보호자'}님! 🐾</Text>
                    <Text style={styles.location}>{item.location} 날씨는</Text>
                    <View style={styles.temperatureRow}>
                      <Text style={styles.temperature}>{item.temperature}°</Text>
                      <Text style={styles.condition}>· {item.conditionLabel}</Text>
                    </View>
                    <Text style={styles.details}>
                      습도 {item.humidity}%  ·  바람 {item.windSpeed}m/s
                    </Text>
                  </View>

                  <View style={styles.tipPill}>
                    <Ionicons color={colors.seaDeep} name="leaf-outline" size={14} />
                    <Text numberOfLines={2} style={styles.tipText}>
                      {item.tip}
                    </Text>
                  </View>
                </ImageBackground>
              ))}
            </ScrollView>
            <View accessibilityLabel={`${page + 1} / ${weather.length}`} style={styles.pageDots}>
              {weather.map((item, index) => (
                <View
                  key={item.location}
                  style={[styles.pageDot, index === page && styles.pageDotActive]}
                />
              ))}
            </View>
          </>
        )}
      </View>

      <Pressable
        accessibilityRole="button"
        onPress={onPressChatbot}
        style={({ pressed }) => [styles.chatButton, pressed && styles.buttonPressed]}
      >
        <Ionicons color={colors.surface} name="chatbubble-ellipses" size={17} />
        <Text style={styles.chatButtonText}>혼디에게 물어보기</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    shadowColor: colors.primaryInk,
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.1,
    shadowRadius: 13,
    elevation: 3,
  },
  imageArea: {
    height: 174,
    padding: spacing.md,
    justifyContent: 'space-between',
    overflow: 'hidden',
  },
  carousel: {
    height: 174,
  },
  image: {
    width: '100%',
    height: '100%',
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  scrim: {
    ...StyleSheet.absoluteFill,
    width: '100%',
    backgroundColor: overlayColors.whiteVeil,
  },
  heroCharacter: {
    position: 'absolute',
    right: -2,
    bottom: -10,
    width: 139,
    height: 162,
  },
  weatherCopy: {
    maxWidth: '62%',
  },
  greeting: {
    marginBottom: 5,
    color: colors.basalt,
    fontSize: 14,
    fontWeight: '800',
  },
  location: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: '600',
  },
  temperatureRow: {
    marginTop: 1,
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  temperature: {
    color: colors.basalt,
    fontSize: 29,
    fontWeight: '900',
    letterSpacing: -1.2,
  },
  condition: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  details: {
    marginTop: 1,
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '600',
  },
  tipPill: {
    width: '70%',
    minHeight: 35,
    paddingHorizontal: 10,
    paddingVertical: 7,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 12,
    backgroundColor: overlayColors.frostedCard,
  },
  tipText: {
    flex: 1,
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: '600',
    lineHeight: 14,
  },
  pageDots: {
    position: 'absolute',
    right: spacing.sm,
    bottom: spacing.xs,
    flexDirection: 'row',
    gap: 4,
  },
  pageDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: overlayColors.whiteVeil,
  },
  pageDotActive: {
    width: 13,
    backgroundColor: colors.primary,
  },
  stateArea: {
    height: 174,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    backgroundColor: colors.seaSoftLight,
  },
  stateText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '700',
  },
  retryButton: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  retryText: {
    color: colors.seaDeep,
    fontSize: 12,
    fontWeight: '800',
  },
  chatButton: {
    height: 43,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    backgroundColor: colors.primary,
  },
  buttonPressed: {
    opacity: 0.78,
  },
  chatButtonText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '800',
  },
});

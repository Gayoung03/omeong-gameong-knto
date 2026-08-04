import Ionicons from '@expo/vector-icons/Ionicons';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

import type { WeatherSummary } from '../types/home';

const WEATHER_HERO = require('@/assets/images/home-weather-hero.png');

type WeatherHeroProps = {
  weather: WeatherSummary;
  onPressChatbot: () => void;
};

export function WeatherHero({ weather, onPressChatbot }: WeatherHeroProps) {
  return (
    <View style={styles.card}>
      <ImageBackground imageStyle={styles.image} source={WEATHER_HERO} style={styles.imageArea}>
        <View style={styles.scrim} />
        <View style={styles.weatherCopy}>
          <Text style={styles.greeting}>{weather.greeting} 🐾</Text>
          <Text style={styles.location}>{weather.location} 날씨는</Text>
          <View style={styles.temperatureRow}>
            <Text style={styles.temperature}>{weather.temperature}°</Text>
            <Text style={styles.condition}>· {weather.condition}</Text>
          </View>
          <Text style={styles.details}>
            습도 {weather.humidity}%  ·  바람 {weather.windSpeed}m/s
          </Text>
        </View>

        <View style={styles.tipPill}>
          <Ionicons color="#2F715F" name="leaf-outline" size={14} />
          <Text numberOfLines={2} style={styles.tipText}>
            {weather.tip}
          </Text>
        </View>
      </ImageBackground>

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
    borderRadius: 20,
    backgroundColor: colors.surface,
    shadowColor: '#552610',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.1,
    shadowRadius: 13,
    elevation: 3,
  },
  imageArea: {
    height: 174,
    padding: 16,
    justifyContent: 'space-between',
  },
  image: {
    width: '100%',
    height: '100%',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  scrim: {
    ...StyleSheet.absoluteFill,
    width: '70%',
    backgroundColor: 'rgba(255,255,255,0.17)',
  },
  weatherCopy: {
    maxWidth: '62%',
  },
  greeting: {
    marginBottom: 5,
    color: '#222222',
    fontSize: 14,
    fontWeight: '800',
  },
  location: {
    color: '#333333',
    fontSize: 12,
    fontWeight: '600',
  },
  temperatureRow: {
    marginTop: 1,
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  temperature: {
    color: '#171717',
    fontSize: 29,
    fontWeight: '900',
    letterSpacing: -1.2,
  },
  condition: {
    color: '#343434',
    fontSize: 13,
    fontWeight: '700',
  },
  details: {
    marginTop: 1,
    color: '#3E5962',
    fontSize: 11,
    fontWeight: '600',
  },
  tipPill: {
    width: '69%',
    minHeight: 35,
    paddingHorizontal: 10,
    paddingVertical: 7,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.88)',
  },
  tipText: {
    flex: 1,
    color: '#42655C',
    fontSize: 10,
    fontWeight: '600',
    lineHeight: 14,
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

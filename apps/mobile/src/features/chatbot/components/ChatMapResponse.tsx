import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { KakaoPlaceMap } from '@/src/features/places/components/KakaoPlaceMap';
import type { Place } from '@/src/features/places/types/place';
import { colors } from '@/src/theme';

type ChatMapResponseProps = {
  places: Place[];
};

const kakaoJavaScriptKey = process.env.EXPO_PUBLIC_KAKAO_JS_KEY?.trim();

export function ChatMapResponse({ places }: ChatMapResponseProps) {
  const mapPlaces = places.map((place) => ({
    id: place.id,
    name: place.name,
    address: place.address,
    category: place.category,
    latitude: place.latitude,
    longitude: place.longitude,
  }));

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>추천 장소 지도</Text>
          <Text style={styles.description}>혼디가 추천한 장소 {places.length}곳</Text>
        </View>
        <View style={styles.countBadge}>
          <Ionicons color={colors.primary} name="location" size={13} />
          <Text style={styles.countText}>{places.length}</Text>
        </View>
      </View>

      <View style={styles.mapArea}>
        {kakaoJavaScriptKey ? (
          <KakaoPlaceMap appKey={kakaoJavaScriptKey} places={mapPlaces} />
        ) : (
          <View style={styles.mapPlaceholder}>
            <View style={styles.mapIconCircle}>
              <Ionicons color={colors.primary} name="map-outline" size={34} />
            </View>
            <Text style={styles.placeholderTitle}>카카오 지도 API 연결 예정</Text>
            <Text style={styles.placeholderDescription}>
              API 키가 설정되면 실제 위치와 마커가 표시됩니다.
            </Text>
          </View>
        )}
      </View>

      <View style={styles.placeNames}>
        {places.map((place, index) => (
          <View key={place.id} style={styles.placeNameRow}>
            <View style={styles.placeNumber}>
              <Text style={styles.placeNumberText}>{index + 1}</Text>
            </View>
            <Text numberOfLines={1} style={styles.placeName}>
              {place.name}
            </Text>
          </View>
        ))}
      </View>

      <View style={styles.actions}>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push({ pathname: '/place-explorer', params: { view: 'map' } })}
          style={({ pressed }) => [
            styles.actionButton,
            styles.mapButton,
            pressed && styles.pressed,
          ]}
        >
          <Ionicons color={colors.primary} name="map-outline" size={17} />
          <Text style={styles.mapButtonText}>지도 보기</Text>
        </Pressable>
        <Pressable
          accessibilityHint="내 여행 화면에서 일정 추가 기능을 이어서 연결할 수 있습니다"
          accessibilityRole="button"
          onPress={() => router.push('/trips')}
          style={({ pressed }) => [
            styles.actionButton,
            styles.tripButton,
            pressed && styles.pressed,
          ]}
        >
          <Ionicons color={colors.surface} name="calendar-outline" size={17} />
          <Text style={styles.tripButtonText}>일정에 추가하기</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: '100%',
    marginTop: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#F0E5DF',
    borderRadius: 18,
    backgroundColor: colors.surface,
    shadowColor: '#64351E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 2,
  },
  header: {
    paddingHorizontal: 15,
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: '800',
  },
  description: {
    marginTop: 3,
    color: colors.textSecondary,
    fontSize: 10,
  },
  countBadge: {
    minWidth: 36,
    height: 28,
    paddingHorizontal: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    borderRadius: 14,
    backgroundColor: '#FFF3EA',
  },
  countText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: '800',
  },
  mapArea: {
    height: 195,
    marginHorizontal: 12,
    overflow: 'hidden',
    borderRadius: 14,
    backgroundColor: '#FFF8F3',
  },
  mapPlaceholder: {
    flex: 1,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#F4D8C8',
    borderRadius: 14,
    backgroundColor: '#FFF8F3',
  },
  mapIconCircle: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFE9DB',
  },
  placeholderTitle: {
    marginTop: 10,
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: '800',
  },
  placeholderDescription: {
    marginTop: 5,
    color: colors.textSecondary,
    fontSize: 10,
    lineHeight: 15,
    textAlign: 'center',
  },
  placeNames: {
    paddingHorizontal: 14,
    paddingTop: 11,
    gap: 7,
  },
  placeNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  placeNumber: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
  },
  placeNumberText: {
    color: colors.surface,
    fontSize: 10,
    fontWeight: '800',
  },
  placeName: {
    flex: 1,
    color: '#4F4A47',
    fontSize: 11,
    fontWeight: '700',
  },
  actions: {
    padding: 12,
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    minHeight: 42,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 12,
  },
  mapButton: {
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
  },
  tripButton: {
    backgroundColor: colors.primary,
  },
  mapButtonText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: '800',
  },
  tripButtonText: {
    color: colors.surface,
    fontSize: 11,
    fontWeight: '800',
  },
  pressed: {
    opacity: 0.68,
  },
});

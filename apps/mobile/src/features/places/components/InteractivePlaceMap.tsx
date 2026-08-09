import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

import type { Place } from '../types/place';
import { KakaoPlaceMap } from './KakaoPlaceMap';

type InteractivePlaceMapProps = {
  places: Place[];
};

const kakaoJavaScriptKey = process.env.EXPO_PUBLIC_KAKAO_JS_KEY?.trim();

export function InteractivePlaceMap({ places }: InteractivePlaceMapProps) {
  if (!kakaoJavaScriptKey) {
    return <MapConfigurationNotice />;
  }

  const mapPlaces = places.map((place) => ({
    id: place.id,
    name: place.name,
    address: place.address,
    category: place.category,
    latitude: place.latitude,
    longitude: place.longitude,
  }));

  return (
    <View style={styles.container}>
      <KakaoPlaceMap appKey={kakaoJavaScriptKey} places={mapPlaces} />
      <View pointerEvents="none" style={styles.summary}>
        <Text style={styles.summaryTitle}>추천 장소 {places.length}곳</Text>
        <Text style={styles.summaryDescription}>마커를 누르면 장소 정보를 볼 수 있어요</Text>
      </View>
    </View>
  );
}

function MapConfigurationNotice() {
  return (
    <View style={styles.notice}>
      <View style={styles.noticeIcon}>
        <Ionicons color="#188F7B" name="map-outline" size={32} />
      </View>
      <Text style={styles.noticeTitle}>카카오 지도 연결이 필요해요</Text>
      <Text style={styles.noticeDescription}>
        JavaScript 키를 설정하면 실제 장소 위치와 확대·축소 기능이 표시됩니다.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    marginHorizontal: 16,
    marginBottom: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#DCEEEB',
    borderRadius: 18,
    backgroundColor: '#EEF8F7',
  },
  summary: {
    position: 'absolute',
    right: 12,
    bottom: 12,
    left: 12,
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderRadius: 13,
    backgroundColor: 'rgba(255,255,255,0.94)',
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
    shadowRadius: 6,
    elevation: 2,
  },
  summaryTitle: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: '800',
  },
  summaryDescription: {
    marginTop: 2,
    color: colors.textSecondary,
    fontSize: 10,
  },
  notice: {
    flex: 1,
    marginHorizontal: 16,
    marginBottom: 16,
    paddingHorizontal: 28,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#DCEEEB',
    borderRadius: 18,
    backgroundColor: '#F3FBFA',
  },
  noticeIcon: {
    width: 64,
    height: 64,
    marginBottom: 14,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E0F4F0',
  },
  noticeTitle: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: '800',
  },
  noticeDescription: {
    maxWidth: 270,
    marginTop: 7,
    color: colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
});

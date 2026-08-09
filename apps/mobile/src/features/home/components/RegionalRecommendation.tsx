import Ionicons from '@expo/vector-icons/Ionicons';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

import { homeRegions } from '../data/homeRegions';
import type { PlaceRegion } from '@/src/features/places/types/place';
import { SectionHeader } from './SectionHeader';

const JEJU_MAP = require('@/assets/illustrations/jeju-region-map.png');

type RegionalRecommendationProps = {
  onPressRegion: (region: PlaceRegion) => void;
  onPressViewAll: () => void;
};

export function RegionalRecommendation({
  onPressRegion,
  onPressViewAll,
}: RegionalRecommendationProps) {
  return (
    <View>
      <SectionHeader actionLabel="전체보기" onPressAction={onPressViewAll} title="제주 권역별 추천 장소" />
      <View style={styles.mapCard}>
        <View style={styles.mapVisual}>
          <Image resizeMode="contain" source={JEJU_MAP} style={styles.mapImage} />
          <Pressable
            accessibilityLabel="제주 권역별 추천 장소 전체보기"
            onPress={onPressViewAll}
            style={({ pressed }) => [styles.mapBackgroundButton, pressed && styles.pressed]}
          />
          {homeRegions.map((region) => (
            <Pressable
              accessibilityLabel={`${region.label} 추천 장소 보기`}
              accessibilityRole="button"
              key={region.id}
              onPress={() => onPressRegion(region.label)}
              style={({ pressed }) => [
                styles.regionButton,
                { left: region.left, top: region.top },
                pressed && styles.regionButtonPressed,
              ]}
            >
              <Ionicons color={colors.primary} name="paw" size={10} />
              <Text numberOfLines={2} style={styles.regionLabel}>
                {region.label}
              </Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.mapCaption}>
          <Text style={styles.captionTitle}>우리 아이와 어디로 갈까요?</Text>
          <Text style={styles.captionDescription}>제주 6개 권역의 추천 장소를 둘러보세요</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  mapCard: {
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E5F3F1',
    borderRadius: 18,
    backgroundColor: '#F3FCFC',
  },
  mapVisual: {
    width: '100%',
    aspectRatio: 2,
    backgroundColor: '#F3FCFC',
  },
  mapBackgroundButton: {
    ...StyleSheet.absoluteFill,
  },
  pressed: {
    opacity: 0.75,
  },
  mapImage: {
    width: '100%',
    height: '100%',
  },
  regionButton: {
    position: 'absolute',
    width: 86,
    minHeight: 32,
    marginLeft: -43,
    marginTop: -16,
    paddingHorizontal: 5,
    paddingVertical: 4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    borderWidth: 1,
    borderColor: 'rgba(255,122,69,0.22)',
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.9)',
    shadowColor: '#4D321F',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
    shadowRadius: 4,
    elevation: 2,
  },
  regionButtonPressed: {
    opacity: 0.72,
    transform: [{ scale: 0.96 }],
  },
  regionLabel: {
    flexShrink: 1,
    color: colors.textPrimary,
    fontSize: 9,
    fontWeight: '800',
    lineHeight: 11,
    textAlign: 'center',
  },
  mapCaption: {
    minHeight: 49,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  captionTitle: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  captionDescription: {
    flexShrink: 1,
    color: colors.textSecondary,
    fontSize: 10,
  },
});

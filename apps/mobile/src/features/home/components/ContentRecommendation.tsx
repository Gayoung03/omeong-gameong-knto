import Ionicons from '@expo/vector-icons/Ionicons';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';

import type { EditorialCard } from '../types/home';
import { SectionHeader } from './SectionHeader';

import { colors, overlayColors } from '@/src/theme';

type ContentRecommendationProps = {
  cards: EditorialCard[];
};

export function ContentRecommendation({ cards }: ContentRecommendationProps) {
  return (
    <View>
      <SectionHeader title="제주 여행 이야기" />
      <View style={styles.grid}>
        {cards.map((card) => (
          <Pressable
            accessibilityRole="button"
            key={card.id}
            style={({ pressed }) => [styles.card, pressed && styles.pressed]}
          >
            <ImageBackground
              imageStyle={styles.image}
              resizeMode="cover"
              source={{ uri: card.imageUrl }}
              style={styles.background}
            >
              <View style={styles.scrim} />
              <Text style={styles.title}>{card.title}</Text>
              <View style={styles.arrowCircle}>
                <Ionicons color={colors.textPrimary} name="chevron-forward" size={16} />
              </View>
            </ImageBackground>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  card: {
    width: '48.8%',
    aspectRatio: 1.45,
    overflow: 'hidden',
    borderRadius: 15,
    backgroundColor: colors.divider,
  },
  pressed: {
    opacity: 0.7,
  },
  background: {
    flex: 1,
    padding: 11,
    justifyContent: 'space-between',
  },
  image: {
    width: '100%',
    height: '100%',
    borderRadius: 15,
  },
  scrim: {
    ...StyleSheet.absoluteFill,
    backgroundColor: overlayColors.dim,
  },
  title: {
    maxWidth: '88%',
    color: colors.surface,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 18,
    textShadowColor: overlayColors.textShadow,
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  arrowCircle: {
    width: 27,
    height: 27,
    alignSelf: 'flex-end',
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: overlayColors.frostedCard,
  },
});

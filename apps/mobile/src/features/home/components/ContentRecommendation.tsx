import Ionicons from '@expo/vector-icons/Ionicons';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';

import type { EditorialStory } from '../types/home';
import { SectionHeader } from '@/src/components/ui/SectionHeader';

import { colors, overlayColors, radius, spacing } from '@/src/theme';

type ContentRecommendationProps = {
  stories: EditorialStory[];
  onPressStory: (story: EditorialStory) => void;
};

export function ContentRecommendation({ stories, onPressStory }: ContentRecommendationProps) {
  return (
    <View>
      <SectionHeader title="제주 여행 이야기" style={styles.sectionHeader} />
      <View style={styles.grid}>
        {stories.map((story) => (
          <Pressable
            accessibilityRole="button"
            key={story.id}
            onPress={() => onPressStory(story)}
            style={({ pressed }) => [styles.card, pressed && styles.pressed]}
          >
            <ImageBackground
              imageStyle={styles.image}
              resizeMode="cover"
              source={{ uri: story.heroImageUrl }}
              style={styles.background}
            >
              <View style={styles.scrim} />
              <Text style={styles.title}>{story.cardTitle}</Text>
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
  sectionHeader: {
    marginBottom: spacing.sm + spacing.xs,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  card: {
    width: '48.8%',
    aspectRatio: 1.45,
    overflow: 'hidden',
    borderRadius: radius.lg,
    backgroundColor: colors.divider,
  },
  pressed: {
    opacity: 0.7,
  },
  background: {
    flex: 1,
    padding: spacing.md,
    justifyContent: 'space-between',
  },
  image: {
    width: '100%',
    height: '100%',
    borderRadius: radius.lg,
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

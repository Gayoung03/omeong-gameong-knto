import Ionicons from '@expo/vector-icons/Ionicons';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';

import type { EditorialStory } from '../types/home';
import { SectionHeader } from '@/src/components/ui/SectionHeader';

import { colors, overlayColors, radius, spacing } from '@/src/theme';

const PREPARATION_IMAGE = require('@/assets/images/travel-preparation-card.png');

type ContentRecommendationProps = {
  stories: EditorialStory[];
  showPreparation: boolean;
  onPressPreparation: () => void;
  onPressStory: (story: EditorialStory) => void;
};

export function ContentRecommendation({
  stories,
  showPreparation,
  onPressPreparation,
  onPressStory,
}: ContentRecommendationProps) {
  const visibleStories = stories.slice(0, showPreparation ? 3 : 4);

  return (
    <View>
      <SectionHeader title="제주 여행 이야기" style={styles.sectionHeader} />
      {!showPreparation && visibleStories.length === 0 ? (
        <View style={styles.emptyCard}>
          <Ionicons color={colors.primary} name="paw-outline" size={20} />
          <Text style={styles.emptyText}>새로운 제주 이야기를 준비하고 있다멍.</Text>
        </View>
      ) : (
        <View style={styles.grid}>
          {showPreparation ? (
            <Pressable
              accessibilityLabel="출발 전 체크리스트 열기"
              accessibilityRole="button"
              onPress={onPressPreparation}
              style={({ pressed }) => [styles.card, pressed && styles.pressed]}
            >
              <ImageBackground
                imageStyle={styles.image}
                resizeMode="cover"
                source={PREPARATION_IMAGE}
                style={styles.background}
              >
                <View style={styles.scrim} />
                <Text style={styles.title}>출발 전 체크리스트{`\n`}미리 챙겼개?</Text>
                <View style={styles.arrowCircle}>
                  <Ionicons color={colors.textPrimary} name="chevron-forward" size={16} />
                </View>
              </ImageBackground>
            </Pressable>
          ) : null}
          {visibleStories.map((story) => (
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
      )}
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
  emptyCard: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.lg,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  emptyText: { color: colors.textSecondary, fontSize: 13, fontWeight: '600' },
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

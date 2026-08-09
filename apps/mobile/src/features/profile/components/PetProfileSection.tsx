import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  LayoutChangeEvent,
  NativeSyntheticEvent,
  NativeScrollEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { Card } from '@/src/components/ui/Card';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { Pet } from '@/src/types/pet';

import { PetProfileCard } from './PetProfileCard';

type PetProfileSectionProps = {
  pets: Pet[];
};

const PEEK_RATIO = 0.82;

function EmptyPetState() {
  const router = useRouter();

  return (
    <Pressable accessibilityLabel="반려동물 등록" accessibilityRole="button" onPress={() => router.push('/pets/new')}>
      <Card style={styles.emptyCard}>
        <Ionicons color={colors.primary} name="add" size={22} />
        <Text style={styles.emptyLabel}>반려동물을 등록해주세요</Text>
      </Card>
    </Pressable>
  );
}

export function PetProfileSection({ pets }: PetProfileSectionProps) {
  const [containerWidth, setContainerWidth] = useState(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const pageCount = pets.length;
  const snapInterval = containerWidth > 0 ? containerWidth * PEEK_RATIO + spacing.sm : undefined;

  const handleLayout = (event: LayoutChangeEvent) => {
    setContainerWidth(event.nativeEvent.layout.width);
  };

  const handleMomentumScrollEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (!snapInterval) {
      return;
    }
    const index = Math.round(event.nativeEvent.contentOffset.x / snapInterval);
    setActiveIndex(index);
  };

  if (pets.length === 0) {
    return <EmptyPetState />;
  }

  return (
    <View onLayout={handleLayout}>
      <ScrollView
        decelerationRate="fast"
        horizontal
        onMomentumScrollEnd={handleMomentumScrollEnd}
        showsHorizontalScrollIndicator={false}
        snapToAlignment="start"
        snapToInterval={snapInterval}
      >
        {pets.map((pet, index) => (
          <View
            key={pet.petId}
            style={[styles.page, index < pets.length - 1 && styles.pageSpacing]}
          >
            <PetProfileCard pet={pet} />
          </View>
        ))}
      </ScrollView>
      {pageCount > 1 && (
        <View style={styles.dots}>
          {Array.from({ length: pageCount }).map((_, index) => (
            <View key={index} style={[styles.dot, index === activeIndex && styles.dotActive]} />
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  dot: {
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 6,
    width: 6,
  },
  dotActive: {
    backgroundColor: colors.primary,
  },
  dots: {
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    marginTop: spacing.sm,
  },
  emptyCard: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  emptyLabel: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  page: {
    width: `${PEEK_RATIO * 100}%`,
  },
  pageSpacing: {
    marginRight: spacing.sm,
  },
});

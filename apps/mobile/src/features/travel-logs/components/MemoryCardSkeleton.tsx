import { StyleSheet, View } from 'react-native';

import { colors, radius, spacing } from '@/src/theme';

type MemoryCardSkeletonProps = {
  size: 'large' | 'small';
};

export function MemoryCardSkeleton({ size }: MemoryCardSkeletonProps) {
  return (
    <View style={styles.container}>
      <View style={[size === 'large' ? styles.imageLarge : styles.imageSmall, styles.skeleton]} />
      <View style={[styles.skeleton, styles.messageLine]} />
      <View style={[styles.skeleton, styles.metaLine]} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs,
  },
  imageLarge: {
    aspectRatio: 1.4,
  },
  imageSmall: {
    aspectRatio: 1,
  },
  metaLine: {
    height: 12,
    width: '70%',
  },
  messageLine: {
    height: 16,
    width: '85%',
  },
  skeleton: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.md,
  },
});

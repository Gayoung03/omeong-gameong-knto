import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, View } from 'react-native';

import { colors, spacing } from '@/src/theme';

import { REVIEW_RATING_MAX } from '../types/review';

type StarRatingProps = {
  rating: number;
  size?: number;
  /** 값이 있으면 별을 눌러 점수를 바꿀 수 있다. 없으면 보기 전용이다. */
  onChange?: (rating: number) => void;
};

export function StarRating({ rating, size = 16, onChange }: StarRatingProps) {
  const stars = Array.from({ length: REVIEW_RATING_MAX }, (_, index) => index + 1);

  return (
    <View style={styles.row}>
      {stars.map((star) =>
        onChange ? (
          <Pressable
            accessibilityLabel={`${star}점`}
            accessibilityRole="button"
            hitSlop={spacing.xs}
            key={star}
            onPress={() => onChange(star)}
          >
            <Ionicons
              color={star <= rating ? colors.warning : colors.border}
              name={star <= rating ? 'star' : 'star-outline'}
              size={size}
            />
          </Pressable>
        ) : (
          <Ionicons
            color={star <= rating ? colors.warning : colors.border}
            key={star}
            name={star <= rating ? 'star' : 'star-outline'}
            size={size}
          />
        ),
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.xs / 2,
  },
});

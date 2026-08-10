import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

export const MAX_INQUIRY_IMAGES = 3;

const THUMBNAIL_SIZE = 92;

type Props = {
  imageUris: string[];
  onAdd: () => void;
  onRemove: (uri: string) => void;
  disabled?: boolean;
};

export function InquiryPhotoPicker({ imageUris, onAdd, onRemove, disabled = false }: Props) {
  const canAdd = imageUris.length < MAX_INQUIRY_IMAGES;

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        {canAdd ? (
          <Pressable
            accessibilityLabel="사진 추가"
            accessibilityRole="button"
            disabled={disabled}
            onPress={onAdd}
            style={styles.addBox}
          >
            <Ionicons color={colors.primary} name="add" size={26} />
            <Text style={styles.addLabel}>사진 추가</Text>
          </Pressable>
        ) : null}

        {imageUris.map((uri) => (
          <View key={uri} style={styles.thumbnailWrapper}>
            <RemoteImage borderRadius={radius.md} style={styles.thumbnail} uri={uri} />
            <Pressable
              accessibilityLabel="사진 삭제"
              accessibilityRole="button"
              hitSlop={spacing.sm}
              onPress={() => onRemove(uri)}
              style={styles.removeButton}
            >
              <Ionicons color={colors.surface} name="close" size={14} />
            </Pressable>
          </View>
        ))}
      </View>

      <Text style={styles.hint}>최대 {MAX_INQUIRY_IMAGES}장</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  addBox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing.xs,
    height: THUMBNAIL_SIZE,
    justifyContent: 'center',
    width: THUMBNAIL_SIZE,
  },
  addLabel: {
    color: colors.primary,
    fontSize: typography.body.fontSize - 4,
    fontWeight: '600',
  },
  container: {
    gap: spacing.sm,
  },
  hint: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 4,
  },
  removeButton: {
    alignItems: 'center',
    backgroundColor: overlayColors.scrim,
    borderRadius: 9999,
    height: 22,
    justifyContent: 'center',
    position: 'absolute',
    right: -6,
    top: -6,
    width: 22,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  thumbnail: {
    height: THUMBNAIL_SIZE,
    width: THUMBNAIL_SIZE,
  },
  thumbnailWrapper: {
    position: 'relative',
  },
});

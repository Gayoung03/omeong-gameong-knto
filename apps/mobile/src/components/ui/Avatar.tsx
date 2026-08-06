import Ionicons from '@expo/vector-icons/Ionicons';
import { Image, StyleSheet, View } from 'react-native';

import { colors } from '@/src/theme';

type AvatarProps = {
  uri?: string;
  size?: number;
  fallbackIcon?: keyof typeof Ionicons.glyphMap;
};

export function Avatar({ uri, size = 48, fallbackIcon = 'person' }: AvatarProps) {
  const dimension = { height: size, width: size };

  if (!uri) {
    return (
      <View style={[styles.fallback, dimension]}>
        <Ionicons color={colors.textSecondary} name={fallbackIcon} size={size * 0.5} />
      </View>
    );
  }

  return <Image source={{ uri }} style={[styles.image, dimension]} />;
}

const styles = StyleSheet.create({
  fallback: {
    alignItems: 'center',
    backgroundColor: colors.border,
    borderRadius: 9999,
    justifyContent: 'center',
  },
  image: {
    borderRadius: 9999,
  },
});

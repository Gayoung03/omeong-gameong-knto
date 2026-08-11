import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { colors, spacing } from '@/src/theme';

type ProfileImagePickerProps = {
  imageUri?: string;
  onPress: () => void;
};

export function ProfileImagePicker({ imageUri, onPress }: ProfileImagePickerProps) {
  return (
    <Pressable onPress={onPress} style={styles.container}>
      <Avatar size={140} uri={imageUri} />
      <View style={styles.editButtonOverlay}>
        <Ionicons color={colors.surface} name="camera" size={20} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: spacing.lg,
    position: 'relative',
  },
  editButtonOverlay: {
    alignItems: 'center',
    backgroundColor: colors.sea,
    borderRadius: 9999,
    bottom: spacing.xs,
    height: 40,
    justifyContent: 'center',
    position: 'absolute',
    right: spacing.xs,
    width: 40,
  },
});

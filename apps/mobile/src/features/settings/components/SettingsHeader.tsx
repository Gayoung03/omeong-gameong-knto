import { useSafeBack } from '@/src/hooks/useSafeBack';
import { StyleSheet, Text, View } from 'react-native';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, spacing, typography } from '@/src/theme';

const ICON_SIZE = 24;
const ICON_BUTTON_TOUCH_SIZE = 44;

export function SettingsHeader() {
  const goBack = useSafeBack('/profile');

  return (
    <View style={styles.header}>
      <IconButton icon="close-outline" onPress={goBack} size={ICON_SIZE} />
      <Text style={styles.title}>설정</Text>
      <View style={styles.spacer} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
  },
  spacer: {
    height: ICON_BUTTON_TOUCH_SIZE,
    width: ICON_BUTTON_TOUCH_SIZE,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize,
    fontWeight: typography.title.fontWeight,
  },
});

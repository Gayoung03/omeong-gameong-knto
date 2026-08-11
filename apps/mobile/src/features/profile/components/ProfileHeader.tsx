import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, spacing, typography } from '@/src/theme';

export function ProfileHeader() {
  const router = useRouter();

  return (
    <View style={styles.header}>
      <Text style={styles.title}>마이페이지</Text>
      <IconButton icon="settings-outline" onPress={() => router.push('/settings')} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
});

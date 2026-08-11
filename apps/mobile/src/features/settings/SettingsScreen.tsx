import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ListItem } from '@/src/components/ui/ListItem';
import { LogoutConfirmModal } from '@/src/features/auth/components/LogoutConfirmModal';
import { useLogout } from '@/src/features/auth/hooks/useLogout';
import { colors, spacing } from '@/src/theme';

import { SettingsHeader } from './components/SettingsHeader';
import { settingsMenuItems, type SettingsMenuItem } from './data/settingsMenuItems';

export function SettingsScreen() {
  const router = useRouter();
  const { isConfirmVisible, requestLogout, cancelLogout, confirmLogout } = useLogout();

  // 아직 연결되지 않은 메뉴는 undefined를 돌려줘 눌러도 아무 일이 없다.
  const resolvePress = ({ route, action }: SettingsMenuItem) => {
    if (route) return () => router.push(route);
    if (action === 'logout') return requestLogout;
    return undefined;
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <SettingsHeader />
        {settingsMenuItems.map((item) => (
          <ListItem
            key={item.label}
            label={item.label}
            onPress={resolvePress(item)}
            trailingText={item.trailingText}
          />
        ))}
      </ScrollView>

      <LogoutConfirmModal
        onCancel={cancelLogout}
        onConfirm={confirmLogout}
        visible={isConfirmVisible}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});

import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { LogoutConfirmModal } from '@/src/features/auth/components/LogoutConfirmModal';
import { useLogout } from '@/src/features/auth/hooks/useLogout';
import { colors } from '@/src/theme';

export function ProfileFooterLinks() {
  const router = useRouter();
  const { isConfirmVisible, requestLogout, cancelLogout, confirmLogout } = useLogout();

  return (
    <View style={styles.utilityMenu}>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push('/inquiries')}
        style={({ pressed }) => [styles.utilityItem, pressed && styles.utilityItemPressed]}
      >
        <Text style={styles.utilityText}>1:1 문의</Text>
      </Pressable>

      <View style={styles.utilityDivider} />

      <Pressable
        accessibilityRole="button"
        onPress={requestLogout}
        style={({ pressed }) => [styles.utilityItem, pressed && styles.utilityItemPressed]}
      >
        <Text style={styles.utilityText}>로그아웃</Text>
      </Pressable>

      <LogoutConfirmModal
        onCancel={cancelLogout}
        onConfirm={confirmLogout}
        visible={isConfirmVisible}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  utilityDivider: {
    backgroundColor: colors.divider,
    height: 22,
    width: 1,
  },
  utilityItem: {
    alignItems: 'center',
    alignSelf: 'stretch',
    flex: 1,
    justifyContent: 'center',
  },
  utilityItemPressed: {
    opacity: 0.6,
  },
  // 카드가 아니라 하단 탭 바로 위에 붙는 얇은 보조 메뉴 바라서 모서리 곡률·그림자를 두지 않는다.
  utilityMenu: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderBottomColor: colors.divider,
    borderBottomWidth: 1,
    borderTopColor: colors.divider,
    borderTopWidth: 1,
    flexDirection: 'row',
    height: 46,
  },
  utilityText: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: '500',
  },
});

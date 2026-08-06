import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { Card } from '@/src/components/ui/Card';
import { colors, spacing, typography } from '@/src/theme';
import type { User } from '@/src/types/user';

type UserProfileSectionProps = {
  user: User;
};

export function UserProfileSection({ user }: UserProfileSectionProps) {
  const router = useRouter();

  return (
    <Pressable
      accessibilityLabel="프로필 관리"
      accessibilityRole="button"
      onPress={() => router.push('/profile-edit')}
    >
      <Card padding="sm" style={styles.card}>
        <Avatar size={48} uri={user.profileImage} />
        <View style={styles.info}>
          <Text style={styles.nickname}>{user.nickname}</Text>
          <Text style={styles.email}>{user.email}</Text>
        </View>
        <View style={styles.action}>
          <Text style={styles.actionLabel}>프로필 관리</Text>
          <Ionicons color={colors.textSecondary} name="chevron-forward" size={16} />
        </View>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  action: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs / 2,
  },
  actionLabel: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
  },
  card: {
    alignItems: 'center',
    flexDirection: 'row',
  },
  email: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    marginTop: spacing.xs / 2,
  },
  info: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  nickname: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
});

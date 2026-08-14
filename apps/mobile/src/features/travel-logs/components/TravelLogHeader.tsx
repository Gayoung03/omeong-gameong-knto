import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, radius, spacing, typography } from '@/src/theme';

export function TravelLogHeader() {
  const router = useRouter();

  return (
    <View style={styles.header}>
      <View style={styles.titleRow}>
        <View style={styles.titleGroup}>
          <IconButton
            accessibilityLabel="뒤로 가기"
            icon="chevron-back"
            onPress={() => router.back()}
          />
          <Text style={styles.title}>여행 기록</Text>
        </View>
        {/* 헤더 보조 액션이라 공통 Button 대신 이 화면 전용 pill 스타일을 쓴다. */}
        <Pressable
          accessibilityLabel="새로운 순간 남기기"
          accessibilityRole="button"
          onPress={() => router.push('/travel-logs/new-moment')}
          style={({ pressed }) => [styles.createButton, pressed && styles.createButtonPressed]}
        >
          {/* Ionicons에는 '카메라+' 글리프가 없어 카메라 위에 작은 + 배지를 얹는다. */}
          <View style={styles.createButtonIcon}>
            <Ionicons color={colors.primary} name="camera-outline" size={18} />
            <View style={styles.createButtonIconBadge}>
              <Ionicons color={colors.primary} name="add" size={9} />
            </View>
          </View>
          <Text style={styles.createButtonDot}>•</Text>
          <Text style={styles.createButtonLabel}>새로운 순간 남기기</Text>
        </Pressable>
      </View>
      <Text style={styles.subtitle}>함께한 제주 여행의 소중한 순간들</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  createButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs + 2,
    height: 40,
    justifyContent: 'center',
    paddingHorizontal: spacing.md - 2,
  },
  createButtonDot: {
    color: colors.primary,
    fontSize: 12,
  },
  createButtonIcon: {
    position: 'relative',
  },
  createButtonIconBadge: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 9999,
    bottom: -2,
    justifyContent: 'center',
    position: 'absolute',
    right: -4,
  },
  createButtonLabel: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: '600',
  },
  createButtonPressed: {
    opacity: 0.7,
  },
  header: {
    gap: spacing.xs,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    paddingLeft: spacing.xs,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize,
    fontWeight: typography.title.fontWeight,
  },
  titleGroup: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
});

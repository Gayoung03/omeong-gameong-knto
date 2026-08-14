import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, spacing, typography } from '@/src/theme';

const ICON_SIZE = 24;
const ICON_BUTTON_TOUCH_SIZE = 44;

type Props = {
  title: string;
};

/** 하위 화면 공통 헤더. 뒤로가기 + 가운데 정렬 타이틀. */
export function ScreenHeader({ title }: Props) {
  const router = useRouter();

  return (
    <View style={styles.header}>
      <IconButton
        accessibilityLabel="뒤로 가기"
        icon="chevron-back"
        onPress={() => router.back()}
        size={ICON_SIZE}
      />
      <Text style={styles.title}>{title}</Text>
      {/* 타이틀을 정확히 가운데 두기 위한 좌우 대칭 여백 */}
      <View style={styles.spacer} />
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  spacer: {
    height: ICON_BUTTON_TOUCH_SIZE,
    width: ICON_BUTTON_TOUCH_SIZE,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize - 2,
    fontWeight: '700',
  },
});

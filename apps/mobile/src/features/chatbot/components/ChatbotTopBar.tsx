import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

type Props = {
  onNewChat: () => void;
  onOpenSidebar: () => void;
  /** 지금 열려 있는 대화 이름. 첫 질문 전에는 "새 대화". */
  title: string;
};

/**
 * 챗봇 화면 전용 줄. `AppHeader` 아래에 놓는다.
 *
 * **공통 `AppHeader` 를 고치지 않는 이유**는 그 파일이 하단 탭 다섯 화면이 함께
 * 쓰는 공통 파일이라, 챗봇에만 필요한 버튼 두 개 때문에 다섯 화면의 헤더가
 * 흔들리기 때문이다. `ScreenTitleBar` 도 왼쪽 버튼 자리가 없다.
 *
 * 제목을 가운데 두는 이유는, 창 전환 수단이 사이드바뿐이라(C-1) **지금 어느
 * 대화에 있는지**가 화면에 늘 보여야 하기 때문이다.
 */
export function ChatbotTopBar({ onNewChat, onOpenSidebar, title }: Props) {
  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityLabel="대화 목록 열기"
        accessibilityRole="button"
        hitSlop={8}
        onPress={onOpenSidebar}
        style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
      >
        <Ionicons color={colors.textPrimary} name="menu" size={21} />
      </Pressable>

      <Text numberOfLines={1} style={styles.title}>
        {title}
      </Text>

      <Pressable
        accessibilityLabel="새 대화 시작"
        accessibilityRole="button"
        hitSlop={8}
        onPress={onNewChat}
        style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
      >
        <Ionicons color={colors.textPrimary} name="create-outline" size={20} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    minHeight: 44,
    paddingHorizontal: spacing.sm,
  },
  iconButton: {
    alignItems: 'center',
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  pressed: {
    opacity: 0.68,
  },
  title: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});

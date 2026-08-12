import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

export const SCREEN_TITLE_BAR_HEIGHT = 48;

type Props = {
  title: string;
  /** 화면 고유 액션. 없으면 오른쪽은 비워둔다. */
  right?: ReactNode;
};

/**
 * `AppHeader` 아래에 놓는 화면 제목 줄.
 *
 * 브랜드 바는 모든 탭에서 같고, 화면마다 다른 제목·액션은 여기서 처리한다.
 */
export function ScreenTitleBar({ title, right }: Props) {
  return (
    <View style={styles.bar}>
      <Text style={styles.title}>{title}</Text>
      {right ?? null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    alignItems: 'center',
    flexDirection: 'row',
    height: SCREEN_TITLE_BAR_HEIGHT,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize,
    fontWeight: '700',
  },
});

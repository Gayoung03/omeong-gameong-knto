import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/src/components/ui/Button';
import { colors, spacing, typography } from '@/src/theme';

type MessageStateProps = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  children?: React.ReactNode;
};

function MessageState({ icon, title, description, children }: MessageStateProps) {
  return (
    <View style={styles.container}>
      <View style={styles.iconCircle}>
        <Ionicons color={colors.iconGray} name={icon} size={28} />
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>
      {children}
    </View>
  );
}

/**
 * 기록이 하나도 없는 상태.
 *
 * **버튼을 두지 않는다.** 여기에도 '새로운 순간 남기기' 가 있었는데 `onPress` 가
 * 없어 눌러도 아무 일이 안 났다. 같은 화면 오른쪽 위에 **동작하는 같은 버튼**이
 * 이미 있어서, 하나를 살리는 것보다 **죽은 쪽을 없애는 편**이 낫다 —
 * 같은 이름의 버튼 둘 중 하나만 먹히면 사용자는 앱이 고장났다고 읽는다.
 */
export function TravelLogEmptyState() {
  return (
    <MessageState
      description="위 '새로운 순간 남기기' 로 첫 기록을 만들어 보세요"
      icon="camera-outline"
      title="아직 남겨진 여행 기록이 없어요"
    />
  );
}

/** 검색·필터 조건에 맞는 결과가 없는 상태 */
export function TravelLogNoResultsState({ onResetFilters }: { onResetFilters: () => void }) {
  return (
    <MessageState
      description="검색어나 선택한 날짜를 다시 확인해 주세요"
      icon="search-outline"
      title="조건에 맞는 여행 기록이 없어요"
    >
      <Button label="필터 초기화" onPress={onResetFilters} variant="outline" />
    </MessageState>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.xl,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    borderRadius: 9999,
    height: 64,
    justifyContent: 'center',
    marginBottom: spacing.xs,
    width: 64,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});

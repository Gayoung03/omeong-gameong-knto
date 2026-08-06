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

/** 기록이 하나도 없는 상태 */
export function TravelLogEmptyState() {
  return (
    <MessageState
      description="반려동물과 함께한 소중한 순간을 남겨보세요"
      icon="camera-outline"
      title="아직 남겨진 여행 기록이 없어요"
    >
      {/* TODO: 새로운 로그 생성 화면 연결 */}
      <Button label="새로운 순간 남기기" variant="primary" />
    </MessageState>
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

/** 데이터를 불러오지 못한 상태. 기술적인 오류 메시지는 노출하지 않는다. */
export function TravelLogErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <MessageState
      description="잠시 후 다시 시도해 주세요"
      icon="cloud-offline-outline"
      title="여행 기록을 불러오지 못했어요"
    >
      <Button label="다시 시도" onPress={onRetry} variant="primary" />
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

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

/** 등록한 문의가 하나도 없는 상태 */
export function InquiryEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <MessageState
      description="궁금한 점이 있다면 새 문의를 남겨보세요."
      icon="chatbubble-ellipses-outline"
      title="등록한 문의가 아직 없어요."
    >
      <Button label="새 문의 작성" onPress={onCreate} variant="outline" />
    </MessageState>
  );
}

/** 선택한 상태 탭에 해당하는 문의가 없는 상태 */
export function InquiryNoResultsState({ statusLabel }: { statusLabel: string }) {
  return (
    <MessageState
      description="다른 탭에서 확인해 보세요."
      icon="funnel-outline"
      title={`${statusLabel} 상태의 문의가 없어요.`}
    />
  );
}

/** 데이터를 불러오지 못한 상태. 기술적인 오류 메시지는 노출하지 않는다. */
export function InquiryErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <MessageState
      description="잠시 후 다시 시도해 주세요."
      icon="cloud-offline-outline"
      title="문의 내역을 불러오지 못했어요."
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

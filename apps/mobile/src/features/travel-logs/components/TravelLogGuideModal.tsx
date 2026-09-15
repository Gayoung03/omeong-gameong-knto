import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

type TravelLogGuideModalProps = {
  visible: boolean;
  /** 닫을 때 "다시 보지 않기" 를 골랐는지 함께 알려준다. */
  onClose: (dontShowAgain: boolean) => void;
};

/** 한 줄에 한 단계. 네 단계를 넘기지 않는다 — 넘기면 읽지 않고 닫는다. */
const STEPS = [
  { icon: 'image-outline', text: '함께한 순간이 담긴 사진 한 장을 고르세요' },
  { icon: 'location-outline', text: '언제, 어디에서 함께했는지 골라요' },
  { icon: 'chatbubble-ellipses-outline', text: '제주 방언과 강아지 일기 중 말투를 고르면' },
  { icon: 'sparkles-outline', text: '손글씨가 얹힌 여행 카드가 만들어져요' },
] as const;

/**
 * 여행 기록을 처음 열었을 때 한 번 뜨는 사용법 안내.
 *
 * **`Alert.alert` 을 쓰지 않는다**(`ConfirmModal` 과 같은 이유 — 웹에서 안 뜬다).
 *
 * 만드는 데 걸리는 시간을 굳이 적어 두는 이유는, **기다리는 이유를 모르면 고장으로
 * 오해하기 때문**이다. 사진 분석·문구 생성·이미지 편집을 차례로 거쳐 40~50초가 걸린다.
 */
export function TravelLogGuideModal({ visible, onClose }: TravelLogGuideModalProps) {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  return (
    <Modal
      animationType="fade"
      onRequestClose={() => onClose(dontShowAgain)}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable
          accessibilityLabel="안내 닫기"
          onPress={() => onClose(dontShowAgain)}
          style={styles.backdrop}
        />

        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <View style={styles.titleRow}>
            <Ionicons color={colors.primary} name="paw" size={20} />
            <Text style={styles.title}>여행 기록, 이렇게 만들어요</Text>
          </View>

          <View style={styles.steps}>
            {STEPS.map((step, index) => (
              <View key={step.text} style={styles.step}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepNumber}>{index + 1}</Text>
                </View>
                <Ionicons color={colors.iconGray} name={step.icon} size={18} />
                <Text style={styles.stepText}>{step.text}</Text>
              </View>
            ))}
          </View>

          <Text style={styles.note}>
            반려동물을 고르지 않아도 만들 수 있어요. 카드 한 장을 만드는 데 40초쯤 걸려요.
          </Text>

          <Pressable
            accessibilityRole="checkbox"
            accessibilityState={{ checked: dontShowAgain }}
            hitSlop={8}
            onPress={() => setDontShowAgain((prev) => !prev)}
            style={styles.checkRow}
          >
            <Ionicons
              color={dontShowAgain ? colors.primary : colors.iconGray}
              name={dontShowAgain ? 'checkbox' : 'square-outline'}
              size={20}
            />
            <Text style={styles.checkLabel}>다시 보지 않기</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={() => onClose(dontShowAgain)}
            style={({ pressed }) => [styles.confirmButton, pressed && styles.pressed]}
          >
            <Text style={styles.confirmLabel}>시작하기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing.md,
    maxWidth: 420,
    padding: spacing.lg,
    width: '100%',
  },
  checkLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
  },
  checkRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
    minHeight: 42,
  },
  confirmButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.sm,
    justifyContent: 'center',
    minHeight: 48,
  },
  confirmLabel: {
    color: colors.surface,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  note: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
  },
  overlay: {
    alignItems: 'center',
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  pressed: {
    opacity: 0.7,
  },
  step: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  stepBadge: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 9999,
    height: 20,
    justifyContent: 'center',
    width: 20,
  },
  stepNumber: {
    color: colors.surface,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  stepText: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    lineHeight: 19,
  },
  steps: {
    gap: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '700',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
});

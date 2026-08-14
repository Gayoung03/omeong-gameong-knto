import Ionicons from '@expo/vector-icons/Ionicons';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

type TripShareSheetProps = {
  /** 날짜별 저장을 제공할지 여부 (일정이 하나도 없으면 숨긴다) */
  hasSchedules: boolean;
  onPressCopyLink: () => void;
  onPressShareLink: () => void;
  onPressSaveWholeTrip: () => void;
  onPressSaveByDay: () => void;
  onClose: () => void;
};

type ShareMenuItem = {
  key: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  description: string;
  onPress: () => void;
};

export function TripShareSheet({
  hasSchedules,
  onPressCopyLink,
  onPressShareLink,
  onPressSaveWholeTrip,
  onPressSaveByDay,
  onClose,
}: TripShareSheetProps) {
  const menuItems: ShareMenuItem[] = [
    {
      key: 'copy-link',
      icon: 'link-outline',
      label: '링크 복사',
      description: '일정 주소를 클립보드에 복사해요',
      onPress: onPressCopyLink,
    },
    {
      key: 'share-link',
      icon: 'share-social-outline',
      label: '다른 앱으로 공유',
      description: '메시지·카카오톡 등으로 바로 보내요',
      onPress: onPressShareLink,
    },
    {
      key: 'save-whole',
      icon: 'images-outline',
      label: '전체 일정 이미지로 저장',
      description: '여행 전체를 한 장으로 만들어요',
      onPress: onPressSaveWholeTrip,
    },
  ];

  if (hasSchedules) {
    menuItems.push({
      key: 'save-day',
      icon: 'image-outline',
      label: '날짜별 이미지로 저장',
      description: 'Day를 골라서 하루치만 저장해요',
      onPress: onPressSaveByDay,
    });
  }

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel="닫기"
          accessibilityRole="button"
          onPress={onClose}
          style={styles.backdropArea}
        />

        <View style={styles.sheet}>
          <View style={styles.grip} />
          <Text style={styles.title}>공유하기</Text>

          {menuItems.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.key}
              onPress={item.onPress}
              style={styles.menuRow}
            >
              <View style={styles.iconCircle}>
                <Ionicons color={colors.primary} name={item.icon} size={18} />
              </View>
              <View style={styles.menuTexts}>
                <Text style={styles.menuLabel}>{item.label}</Text>
                <Text style={styles.menuDescription}>{item.description}</Text>
              </View>
              <Ionicons color={colors.textTertiary} name="chevron-forward" size={16} />
            </Pressable>
          ))}

          <Pressable accessibilityRole="button" onPress={onClose} style={styles.cancelButton}>
            <Text style={styles.cancelText}>닫기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdropArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
    marginBottom: spacing.xs,
  },
  menuRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm + 4,
    paddingVertical: spacing.sm + 4,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  menuTexts: {
    flex: 1,
  },
  menuLabel: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  menuDescription: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    marginTop: 1,
  },
  cancelButton: {
    alignItems: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.md,
    marginTop: spacing.sm,
    paddingVertical: spacing.sm + 4,
  },
  cancelText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});

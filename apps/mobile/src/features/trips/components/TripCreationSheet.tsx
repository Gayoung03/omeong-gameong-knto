import Ionicons from '@expo/vector-icons/Ionicons';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

type TripCreationSheetProps = {
  visible: boolean;
  onClose: () => void;
  onCreateManually: () => void;
  onRequestRecommendation: () => void;
};

export function TripCreationSheet({
  visible,
  onClose,
  onCreateManually,
  onRequestRecommendation,
}: TripCreationSheetProps) {
  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <Pressable accessibilityLabel="닫기" onPress={onClose} style={styles.dismissArea} />
        <View style={styles.sheet}>
          <View style={styles.grip} />
          <View style={styles.heading}>
            <View>
              <Text style={styles.title}>새 여행 만들기</Text>
              <Text style={styles.description}>원하는 방법으로 여행을 시작해보세요.</Text>
            </View>
            <Pressable accessibilityLabel="닫기" hitSlop={spacing.sm} onPress={onClose}>
              <Ionicons color={colors.textSecondary} name="close" size={22} />
            </Pressable>
          </View>

          <CreationOption
            description="날짜와 동행 정보를 정하고 장소를 하나씩 직접 담아요."
            icon="create-outline"
            onPress={onCreateManually}
            title="직접 만들기"
          />
          <CreationOption
            description="취향과 조건을 바탕으로 여행 루트를 추천받아요."
            icon="sparkles-outline"
            onPress={onRequestRecommendation}
            title="루트 추천받기"
          />
        </View>
      </View>
    </Modal>
  );
}

function CreationOption({
  description,
  icon,
  onPress,
  title,
}: {
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  title: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.option, pressed && styles.pressed]}
    >
      <View style={styles.iconCircle}>
        <Ionicons color={colors.primary} name={icon} size={23} />
      </View>
      <View style={styles.optionCopy}>
        <Text style={styles.optionTitle}>{title}</Text>
        <Text style={styles.optionDescription}>{description}</Text>
      </View>
      <Ionicons color={colors.textTertiary} name="chevron-forward" size={20} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'flex-end',
  },
  dismissArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    gap: spacing.sm,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.full,
    height: 4,
    marginBottom: spacing.sm,
    width: 40,
  },
  heading: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: spacing.xs,
  },
  option: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 2,
    padding: spacing.md,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  optionCopy: {
    flex: 1,
    gap: 3,
  },
  optionTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  optionDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 19,
  },
  pressed: {
    opacity: 0.65,
  },
});

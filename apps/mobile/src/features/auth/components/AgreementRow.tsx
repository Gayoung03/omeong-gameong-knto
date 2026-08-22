import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type AgreementRowProps = {
  label: string;
  checked: boolean;
  onToggle: () => void;
  /** 값이 있으면 라벨 앞에 [필수] 또는 [선택] 표시가 붙는다. */
  requirement?: 'required' | 'optional';
  /** 값이 있으면 오른쪽에 전문 보기 버튼이 생긴다. */
  onPressDetail?: () => void;
  emphasized?: boolean;
};

export function AgreementRow({
  label,
  checked,
  onToggle,
  requirement,
  onPressDetail,
  emphasized = false,
}: AgreementRowProps) {
  return (
    <View style={styles.row}>
      <Pressable
        accessibilityRole="checkbox"
        accessibilityState={{ checked }}
        hitSlop={spacing.sm}
        onPress={onToggle}
        style={styles.labelArea}
      >
        <View style={[styles.box, checked && styles.boxChecked]}>
          <Ionicons
            color={checked ? colors.surface : colors.textTertiary}
            name="checkmark"
            size={emphasized ? 18 : 15}
          />
        </View>
        <Text style={[styles.label, emphasized && styles.labelEmphasized]}>
          {requirement && (
            <Text style={requirement === 'required' ? styles.required : styles.optional}>
              {requirement === 'required' ? '[필수] ' : '[선택] '}
            </Text>
          )}
          {label}
        </Text>
      </Pressable>

      {onPressDetail && (
        <Pressable
          accessibilityLabel={`${label} 전문 보기`}
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onPressDetail}
        >
          <Ionicons color={colors.textTertiary} name="chevron-forward" size={18} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    height: 22,
    justifyContent: 'center',
    width: 22,
  },
  boxChecked: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  label: {
    color: colors.textSecondary,
    flexShrink: 1,
    fontSize: typography.label.fontSize,
    lineHeight: 20,
  },
  labelArea: {
    alignItems: 'center',
    flexDirection: 'row',
    flexShrink: 1,
    gap: spacing.sm,
  },
  labelEmphasized: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  optional: {
    color: colors.textTertiary,
  },
  required: {
    color: colors.primary,
    fontWeight: '700',
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

type ListItemProps = {
  icon?: keyof typeof Ionicons.glyphMap;
  label: string;
  trailingText?: string;
  onPress?: () => void;
};

export function ListItem({ icon, label, trailingText, onPress }: ListItemProps) {
  return (
    <Pressable onPress={onPress} style={styles.row}>
      <View style={styles.leading}>
        {icon && (
          <View style={styles.iconCircle}>
            <Ionicons color={colors.iconGray} name={icon} size={18} />
          </View>
        )}
        <Text style={[styles.label, icon && styles.labelWithIcon]}>{label}</Text>
      </View>
      {trailingText ? (
        <Text style={styles.trailingText}>{trailingText}</Text>
      ) : (
        <Ionicons color={colors.textSecondary} name="chevron-forward" size={18} />
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    borderRadius: 9999,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  label: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
  },
  labelWithIcon: {
    marginLeft: spacing.sm,
  },
  leading: {
    alignItems: 'center',
    flexDirection: 'row',
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
    paddingVertical: spacing.sm,
  },
  trailingText: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize,
  },
});

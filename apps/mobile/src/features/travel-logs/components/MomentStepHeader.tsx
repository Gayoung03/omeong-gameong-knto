import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '@/src/theme';

type Props = { title: string; step: 1 | 2 | 3; onBack: () => void };

export function MomentStepHeader({ title, step, onBack }: Props) {
  return (
    <>
      <View style={styles.header}>
        <Pressable accessibilityLabel="이전 화면" hitSlop={8} onPress={onBack} style={styles.backButton}>
          <Ionicons color={colors.textPrimary} name="arrow-back" size={24} />
        </Pressable>
        <Text style={styles.title}>{title}</Text>
        <View style={styles.placeholder} />
      </View>
      <View style={styles.progressRow}>
        <Text style={styles.progressLabel}>{step} / 3</Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${((step - 1) / 2) * 100}%` }]} />
          {[1, 2, 3].map((item) => (
            <View
              key={item}
              style={[
                styles.progressDot,
                { left: `${((item - 1) / 2) * 100}%`, marginLeft: item === 1 ? 0 : -8 },
                item <= step && styles.progressDotActive,
                item < step && styles.progressDotDone,
              ]}
            >
              {item < step ? <Ionicons color={colors.surface} name="checkmark" size={10} /> : null}
            </View>
          ))}
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  backButton: { padding: spacing.sm },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  placeholder: { width: 40 },
  progressDot: { alignItems: 'center', backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 8, borderWidth: 2, height: 16, justifyContent: 'center', position: 'absolute', top: -7, width: 16 },
  progressDotActive: { borderColor: colors.primary },
  progressDotDone: { backgroundColor: colors.primary },
  progressFill: { backgroundColor: colors.primary, height: 2 },
  progressLabel: { color: colors.textPrimary, fontSize: 15 },
  progressRow: { alignItems: 'center', flexDirection: 'row', gap: spacing.lg, paddingBottom: spacing.lg, paddingHorizontal: spacing.xl },
  progressTrack: { backgroundColor: colors.border, flex: 1, height: 2, position: 'relative' },
  title: { color: colors.textPrimary, fontSize: 16, fontWeight: '700' },
});

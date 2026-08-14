import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

const steps = ['계정 정보', '반려동물 정보', '여행 스타일'];

export function SignupProgress({ currentStep }: { currentStep: number }) {
  return (
    <View style={styles.container}>
      <View style={styles.track} />
      {steps.map((label, index) => {
        const step = index + 1;
        const active = step <= currentStep;

        return (
          <View key={label} style={styles.stepWrapper}>
            <View style={styles.step}>
              <View style={styles.circleHalo}>
                <View style={[styles.circle, active && styles.circleActive]}>
                  <Text style={[styles.number, active && styles.numberActive]}>{step}</Text>
                </View>
              </View>
              <Text style={[styles.label, step === currentStep && styles.labelActive]}>{label}</Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginBottom: 34,
    marginTop: 16,
    position: 'relative',
  },
  track: {
    backgroundColor: colors.divider,
    height: 2,
    left: '16.666%',
    position: 'absolute',
    right: '16.666%',
    top: 16,
  },
  stepWrapper: {
    alignItems: 'center',
    flex: 1,
  },
  step: {
    alignItems: 'center',
    gap: 7,
    width: '100%',
  },
  circleHalo: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    marginTop: -5,
    width: 44,
  },
  circle: {
    alignItems: 'center',
    backgroundColor: colors.border,
    borderColor: colors.border,
    borderRadius: 17,
    borderWidth: 2,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  circleActive: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  number: {
    color: colors.textTertiary,
    fontSize: 13,
    fontWeight: '800',
  },
  numberActive: {
    color: colors.primary,
  },
  label: {
    color: colors.textTertiary,
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'center',
  },
  labelActive: {
    color: colors.primary,
    fontWeight: '800',
  },
});

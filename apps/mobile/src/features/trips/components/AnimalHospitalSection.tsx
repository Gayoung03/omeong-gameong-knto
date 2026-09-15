import Ionicons from '@expo/vector-icons/Ionicons';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { AnimalHospital } from '../types/trip';

type AnimalHospitalSectionProps = {
  hospitals: AnimalHospital[];
  /**
   * 부모가 가로 여백을 주지 않는 화면(여행 상세)에서는 true 로 두고 안에서 여백을 만든다.
   * 추천 결과 화면처럼 내용 전체에 padding 이 있으면 false.
   */
  inset?: boolean;
};

function formatDistance(meters: number): string {
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)}km` : `${meters}m`;
}

function callPhone(phone: string) {
  void Linking.openURL(`tel:${phone.replace(/[^0-9+]/g, '')}`);
}

/**
 * 숙소·동선 근처 동물병원 안전망. 서버가 응답 시점에 계산해 최대 3곳을 내려준다.
 *
 * 영업시간 데이터가 없어 `is24Hours` 는 이름의 "24시" 로만 판정한다 — 그래서
 * 진료 시간은 전화로 확인하라는 안내를 같이 둔다. 병원이 없으면 섹션을 숨긴다.
 */
export function AnimalHospitalSection({ hospitals, inset = true }: AnimalHospitalSectionProps) {
  if (hospitals.length === 0) {
    return null;
  }

  const horizontal = inset ? styles.inset : undefined;

  return (
    <View style={styles.section}>
      <Text style={[styles.title, horizontal]}>근처 동물병원</Text>
      <Text style={[styles.subtitle, horizontal]}>
        숙소와 동선에서 가까운 곳이에요. 진료 시간은 전화로 확인해주세요.
      </Text>
      {hospitals.map((hospital) => {
        const phone = hospital.phone;
        return (
          <View key={hospital.id} style={[styles.row, horizontal]}>
            <View style={styles.icon}>
              <Ionicons color={colors.error} name="medkit-outline" size={20} />
            </View>
            <View style={styles.body}>
              <View style={styles.nameRow}>
                <Text numberOfLines={1} style={styles.name}>
                  {hospital.name}
                </Text>
                {hospital.is24Hours ? <Text style={styles.chip}>24시</Text> : null}
              </View>
              <Text numberOfLines={1} style={styles.description}>
                {hospital.address || '주소 정보 없음'}
              </Text>
              <Text style={styles.meta}>{formatDistance(hospital.distanceMeters)} 거리</Text>
            </View>
            {phone ? (
              <Pressable
                accessibilityLabel={`${hospital.name} 전화 걸기`}
                accessibilityRole="button"
                hitSlop={spacing.xs}
                onPress={() => callPhone(phone)}
                style={styles.callButton}
              >
                <Ionicons color={colors.basalt} name="call-outline" size={16} />
                <Text style={styles.callText}>전화</Text>
              </Pressable>
            ) : null}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    paddingTop: spacing.lg,
  },
  inset: {
    paddingHorizontal: spacing.lg - 4,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize - 2,
    fontWeight: '700',
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    paddingBottom: spacing.xs,
    paddingTop: 2,
  },
  row: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 4,
    paddingVertical: spacing.md - 2,
  },
  icon: {
    alignItems: 'center',
    backgroundColor: colors.errorBg,
    borderRadius: radius.md,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  body: {
    flex: 1,
    gap: 2,
  },
  nameRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  name: {
    color: colors.basalt,
    flexShrink: 1,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  chip: {
    backgroundColor: colors.errorBg,
    borderRadius: radius.sm,
    color: colors.error,
    fontSize: typography.micro.fontSize,
    fontWeight: '800',
    overflow: 'hidden',
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  meta: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
  },
  callButton: {
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: 4,
    paddingHorizontal: spacing.md - 2,
    paddingVertical: spacing.sm,
  },
  callText: {
    color: colors.basalt,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
});

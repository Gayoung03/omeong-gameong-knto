import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleSheet, Text, View } from 'react-native';

import { Card } from '@/src/components/ui/Card';
import { colors, spacing, typography } from '@/src/theme';

type DeletionItem = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
};

const deletionItems: DeletionItem[] = [
  {
    icon: 'paw-outline',
    title: '반려동물 정보',
    description: '등록한 반려동물 프로필과 사진이 모두 삭제돼요.',
  },
  {
    icon: 'bookmark-outline',
    title: '저장한 장소·코스',
    description: '저장한 장소와 코스, 여행 계획이 모두 삭제돼요.',
  },
  {
    icon: 'camera-outline',
    title: '여행 로그',
    description: '작성한 여행 로그와 첨부한 사진이 모두 삭제돼요.',
  },
  {
    icon: 'person-outline',
    title: '계정 정보',
    description: '프로필과 앱 설정 등 계정 데이터가 모두 삭제돼요.',
  },
];

/** 탈퇴 시 삭제되는 데이터 목록. 항목은 정책이 바뀌지 않는 한 고정이라 컴포넌트가 직접 들고 있다. */
export function WithdrawDeletionCard() {
  return (
    <Card padding="md">
      {deletionItems.map((item, index) => (
        <View key={item.title}>
          {index > 0 && <View style={styles.divider} />}
          <View style={styles.row}>
            <View style={styles.iconCircle}>
              <Ionicons color={colors.error} name={item.icon} size={18} />
            </View>
            <View style={styles.textGroup}>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.description}>{item.description}</Text>
            </View>
          </View>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  description: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
    lineHeight: 20,
  },
  divider: {
    backgroundColor: colors.border,
    height: 1,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.errorBg,
    borderRadius: 9999,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  textGroup: {
    flex: 1,
    gap: spacing.xs,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
  },
});

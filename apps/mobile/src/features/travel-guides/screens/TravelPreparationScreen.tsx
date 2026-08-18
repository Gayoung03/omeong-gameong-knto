import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors } from '@/src/theme';

/**
 * 마이페이지 "여행 준비 가이드" 진입 화면.
 *
 * 특정 여행과 무관한 **일반 지식 콘텐츠**를 다룬다.
 * 여행별 준비물 체크는 내 여행(trips)의 체크리스트 탭이 담당하므로 역할이 겹치지 않는다.
 *
 * TODO: 이동수단 · 상비약 · 숙소 예절 등 카테고리별 콘텐츠를 붙인다.
 */
export function TravelPreparationScreen() {
  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="여행 준비 가이드" />
      <EmptyState
        description="반려동물과 함께 떠나기 전 알아두면 좋은 정보를 준비하고 있어요."
        icon="bag-outline"
        title="가이드를 준비하고 있어요"
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});

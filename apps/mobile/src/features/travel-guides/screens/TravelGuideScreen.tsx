import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors } from '@/src/theme';

/**
 * 홈 빠른 메뉴의 "여행가이드" 진입 화면.
 *
 * TODO: 가이드 콘텐츠(카테고리 · 아티클 목록)를 붙인다.
 *       백엔드 크롤링 API 가 준비되면 mocks 를 Query 훅으로 교체한다.
 */
export function TravelGuideScreen() {
  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="여행가이드" />
      <EmptyState
        description="제주 여행에 필요한 정보를 모아 곧 보여드릴게요."
        icon="book-outline"
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

import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { StatTile } from '@/src/components/ui/StatTile';
import { useMyReviews } from '@/src/features/reviews/hooks/useMyReviews';
import { useSavedPlaces } from '@/src/features/saved/hooks/useSavedPlaces';
import { spacing } from '@/src/theme';
import type { ActivitySummary } from '@/src/types/profile';

type TravelSummarySectionProps = {
  summary: ActivitySummary;
};

export function TravelSummarySection({ summary }: TravelSummarySectionProps) {
  const router = useRouter();
  // 저장 개수는 기기에 실제로 저장된 목록에서 센다.
  // summary 의 savedPlacesCount 는 목데이터라 쓰지 않는다.
  const { data: savedPlaces = [] } = useSavedPlaces();
  // 리뷰 개수는 서버가 센 total 을 쓴다. items 는 20건짜리 한 페이지다.
  const { data: myReviews } = useMyReviews();

  // 색은 홈 빠른 메뉴와 성격을 맞춘다.
  // 장소=주황, 로그=파랑, 가이드=초록 은 홈에서 쓰는 색과 같고,
  // 리뷰는 홈에 짝이 없어 남은 보라를 쓴다.
  return (
    <View style={styles.grid}>
      <StatTile
        icon="bookmark-outline"
        label="저장한 장소"
        onPress={() => router.push('/saved/places')}
        value={savedPlaces.length}
        variant="orange"
      />
      <StatTile
        icon="camera-outline"
        label="여행 로그"
        onPress={() => router.push('/travel-logs')}
        value={summary.travelLogsCount}
        variant="blue"
      />
      <StatTile
        icon="star-outline"
        label="내가 쓴 리뷰"
        onPress={() => router.push('/reviews/my')}
        value={myReviews?.total ?? 0}
        variant="purple"
      />
      <StatTile
        icon="book-outline"
        label={'여행 준비\n가이드'}
        onPress={() => router.push('/travel-guides/preparation')}
        variant="green"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
});

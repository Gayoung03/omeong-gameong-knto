import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { StatTile } from '@/src/components/ui/StatTile';
import { useSavedPlaces } from '@/src/features/saved/hooks/useSavedPlaces';
import { useSavedRoutes } from '@/src/features/saved/hooks/useSavedRoutes';
import { spacing } from '@/src/theme';
import type { ActivitySummary } from '@/src/types/profile';

type TravelSummarySectionProps = {
  summary: ActivitySummary;
};

export function TravelSummarySection({ summary }: TravelSummarySectionProps) {
  const router = useRouter();
  // 저장 개수는 기기에 실제로 저장된 목록에서 센다.
  // summary 의 savedPlacesCount·savedCoursesCount 는 목데이터라 쓰지 않는다.
  const { data: savedPlaces = [] } = useSavedPlaces();
  const { data: savedRoutes = [] } = useSavedRoutes();

  // 색은 홈 빠른 메뉴와 성격을 맞춘다.
  // 장소=주황, 로그=파랑, 가이드=초록 은 홈에서 쓰는 색과 같다.
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
        icon="map-outline"
        label="저장한 코스"
        onPress={() => router.push('/saved/routes')}
        value={savedRoutes.length}
        variant="yellow"
      />
      <StatTile
        icon="camera-outline"
        label="여행 로그"
        onPress={() => router.push('/travel-logs')}
        value={summary.travelLogsCount}
        variant="blue"
      />
      <StatTile
        icon="bag-outline"
        label="여행 준비 가이드"
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

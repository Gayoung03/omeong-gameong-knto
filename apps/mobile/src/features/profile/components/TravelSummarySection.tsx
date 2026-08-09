import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { StatTile } from '@/src/components/ui/StatTile';
import { spacing } from '@/src/theme';
import type { ActivitySummary } from '@/src/types/profile';

type TravelSummarySectionProps = {
  summary: ActivitySummary;
};

export function TravelSummarySection({ summary }: TravelSummarySectionProps) {
  const router = useRouter();

  return (
    <View style={styles.grid}>
      {/* TODO: 저장한 장소 목록 화면 연결 */}
      <StatTile
        icon="bookmark-outline"
        label="저장한 장소"
        value={summary.savedPlacesCount}
        variant="orange"
      />
      {/* TODO: 저장한 코스 목록 화면 연결 */}
      <StatTile
        icon="map-outline"
        label="저장한 코스"
        value={summary.savedCoursesCount}
        variant="mint"
      />
      <StatTile
        icon="camera-outline"
        label="여행 로그"
        onPress={() => router.push('/travel-logs')}
        value={summary.travelLogsCount}
        variant="orange"
      />
      {/* TODO: 여행 준비 가이드 화면 연결 */}
      <StatTile icon="bag-outline" label="여행 준비 가이드" variant="mint" />
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

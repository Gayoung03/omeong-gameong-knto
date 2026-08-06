import { StyleSheet, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { radius, spacing } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

type PhotoCollageProps = {
  logs: TravelLog[];
};

const TILE_COUNT = 4;

/** 대표 로그 1장 + 작은 로그 3장으로 구성된 콜라주. 항상 완성 이미지(generatedImageUrl)만 사용한다. */
export function PhotoCollage({ logs }: PhotoCollageProps) {
  const tiles = Array.from({ length: TILE_COUNT }, (_, index) => logs[index]);
  const [cover, ...rest] = tiles;

  return (
    <View style={styles.collage}>
      <View style={styles.coverArea}>
        <RemoteImage borderRadius={radius.md} style={styles.tile} uri={cover?.generatedImageUrl} />
      </View>
      <View style={styles.sideArea}>
        {rest.map((log, index) => (
          <View key={log?.logId ?? `placeholder-${index}`} style={styles.sideTile}>
            <RemoteImage borderRadius={radius.md} style={styles.tile} uri={log?.generatedImageUrl} />
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  collage: {
    aspectRatio: 1.15,
    flexDirection: 'row',
    gap: spacing.xs,
  },
  coverArea: {
    flex: 2,
  },
  sideArea: {
    flex: 1,
    gap: spacing.xs,
  },
  sideTile: {
    flex: 1,
  },
  tile: {
    height: '100%',
    width: '100%',
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Image, StyleSheet, View, type ImageResizeMode, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radius } from '@/src/theme';

type RemoteImageProps = {
  uri?: string;
  style?: StyleProp<ViewStyle>;
  resizeMode?: ImageResizeMode;
  borderRadius?: number;
};

/**
 * 로딩 중에는 자리 비율을 유지하는 스켈레톤을, 실패 시 아이콘 플레이스홀더를 보여준다.
 * uri가 아예 없을 때도 동일한 플레이스홀더로 처리해 목록·팝업에서 레이아웃이 흔들리지 않는다.
 */
export function RemoteImage({ uri, style, resizeMode = 'cover', borderRadius = radius.md }: RemoteImageProps) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>(uri ? 'loading' : 'error');

  if (!uri || status === 'error') {
    return (
      <View style={[styles.tile, styles.placeholder, { borderRadius }, style]}>
        <Ionicons color={colors.iconGray} name="image-outline" size={22} />
      </View>
    );
  }

  return (
    <View style={[styles.tile, { borderRadius }, style]}>
      <Image
        onError={() => setStatus('error')}
        onLoad={() => setStatus('loaded')}
        resizeMode={resizeMode}
        source={{ uri }}
        style={[styles.image, { borderRadius }]}
      />
      {status === 'loading' ? (
        <View style={[styles.skeleton, { borderRadius }]} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  image: {
    height: '100%',
    width: '100%',
  },
  placeholder: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    justifyContent: 'center',
  },
  skeleton: {
    backgroundColor: colors.neutralGray,
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  tile: {
    overflow: 'hidden',
  },
});

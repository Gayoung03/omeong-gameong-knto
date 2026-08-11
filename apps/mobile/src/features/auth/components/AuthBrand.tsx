import { Image, StyleSheet, Text, View } from 'react-native';

import { authBrandAssets } from '../config/authBrandAssets';

import { colors } from '@/src/theme';

type AuthBrandProps = {
  compact?: boolean;
  showMascot?: boolean;
};

export function AuthBrand({ compact = false, showMascot = true }: AuthBrandProps) {
  return (
    <View style={styles.container}>
      <View accessibilityLabel="오멍가멍 로고" style={styles.textLogo}>
        <Image
          resizeMode="contain"
          source={authBrandAssets.symbol}
          style={[styles.logoSymbol, compact && styles.logoSymbolCompact]}
        />
        <Text style={[styles.logoText, compact && styles.logoTextCompact]}>오멍가멍</Text>
      </View>

      {!compact && <Text style={styles.tagline}>반려동물과 함께하는 제주 여행의 모든 것</Text>}

      {showMascot && (
        <Image
          accessibilityLabel="혼디 강아지 캐릭터"
          resizeMode="contain"
          source={authBrandAssets.mascot}
          style={[styles.mascot, compact && styles.mascotCompact]}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  textLogo: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
  },
  logoSymbol: {
    height: 54,
    width: 47,
  },
  logoSymbolCompact: {
    height: 38,
    width: 33,
  },
  logoText: {
    color: colors.primaryDeep,
    fontSize: 38,
    fontWeight: '900',
    letterSpacing: -2,
  },
  logoTextCompact: {
    fontSize: 26,
    letterSpacing: -1.2,
  },
  tagline: {
    color: colors.primaryDeep,
    fontSize: 14,
    fontWeight: '600',
    marginTop: 10,
  },
  mascot: {
    height: 210,
    marginTop: 12,
    width: '100%',
  },
  mascotCompact: {
    height: 96,
  },
});

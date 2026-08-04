import Ionicons from '@expo/vector-icons/Ionicons';
import { Image, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

import { authBrandAssets } from '../config/authBrandAssets';

type AuthBrandProps = {
  compact?: boolean;
  showMascot?: boolean;
};

export function AuthBrand({ compact = false, showMascot = true }: AuthBrandProps) {
  return (
    <View style={styles.container}>
      {authBrandAssets.logo ? (
        <Image resizeMode="contain" source={authBrandAssets.logo} style={styles.logoImage} />
      ) : (
        <View accessibilityLabel="오멍가멍 로고" style={styles.textLogo}>
          <View style={styles.logoMark}>
            <Ionicons color="#FFFFFF" name="paw" size={compact ? 18 : 23} />
          </View>
          <Text style={[styles.logoText, compact && styles.logoTextCompact]}>오멍가멍</Text>
        </View>
      )}

      {!compact && <Text style={styles.tagline}>반려동물과 함께하는 제주 여행의 모든 것</Text>}

      {showMascot && (
        <Image
          accessibilityLabel="강아지와 돌하르방 캐릭터"
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
  logoMark: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 14,
    height: 40,
    justifyContent: 'center',
    transform: [{ rotate: '-6deg' }],
    width: 40,
  },
  logoText: {
    color: '#A95620',
    fontSize: 38,
    fontWeight: '900',
    letterSpacing: -2,
  },
  logoTextCompact: {
    fontSize: 26,
    letterSpacing: -1.2,
  },
  logoImage: {
    height: 62,
    width: 240,
  },
  tagline: {
    color: '#A45A2A',
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


import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { brandAssets } from '@/src/config/brandAssets';
import { colors, spacing } from '@/src/theme';

import { NotificationPopup } from './NotificationPopup';

/** 탭 화면의 상단 바 높이. 하위 화면의 공통 헤더와 같은 56px을 사용한다. */
export const APP_HEADER_HEIGHT = 56;

const SYMBOL_WIDTH = 27;
const SYMBOL_HEIGHT = 31;
const BELL_SIZE = 23;
const PROFILE_SIZE = 31;

/**
 * 하단 탭 5개 화면의 공통 상단 바.
 *
 * 왼쪽은 브랜드(심볼 + 오멍가멍), 오른쪽은 알림·프로필이다.
 * 화면 고유의 제목과 액션은 이 바 아래에 `ScreenTitleBar` 로 따로 놓는다.
 *
 * 스크롤과 함께 밀려 올라가지 않도록 **ScrollView 바깥**에 두어야 한다.
 */
type Props = {
  /**
   * 알림 아이콘 동작.
   *
   * - `screen`(기본) — 알림 화면(`/notifications`)으로 이동. 홈·마이페이지처럼 머무는 화면에서 쓴다.
   * - `popup` — 간이 팝업을 겹쳐 띄운다. 입력·대화처럼 흐름이 끊기면 안 되는 화면에서 쓴다.
   */
  notifications?: 'screen' | 'popup';
};

export function AppHeader({ notifications = 'screen' }: Props = {}) {
  const router = useRouter();
  const [popupOpen, setPopupOpen] = useState(false);

  const handlePressNotifications = () => {
    if (notifications === 'popup') {
      setPopupOpen(true);
      return;
    }
    router.push({ params: { title: '알림' }, pathname: '/notifications' });
  };

  return (
    <View style={styles.header}>
      <Pressable
        accessibilityLabel="홈으로 이동"
        accessibilityRole="button"
        hitSlop={10}
        onPress={() => router.push('/')}
        style={({ pressed }) => [styles.brand, pressed && styles.pressed]}
      >
        <Image
          accessibilityLabel="오멍가멍 심볼"
          resizeMode="contain"
          source={brandAssets.symbol}
          style={styles.symbol}
        />
        <Text style={styles.brandText}>오멍가멍</Text>
      </Pressable>

      <View style={styles.actions}>
        <Pressable
          accessibilityLabel="알림"
          accessibilityRole="button"
          hitSlop={10}
          onPress={handlePressNotifications}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <Ionicons color={colors.textPrimary} name="notifications-outline" size={BELL_SIZE} />
        </Pressable>

        <Pressable
          accessibilityLabel="마이페이지"
          accessibilityRole="button"
          hitSlop={10}
          onPress={() => router.push('/profile')}
          style={({ pressed }) => [styles.profileCircle, pressed && styles.pressed]}
        >
          <Image
            accessibilityLabel="혼디 강아지 캐릭터"
            resizeMode="cover"
            source={brandAssets.character.avatar}
            style={styles.profileImage}
          />
        </Pressable>
      </View>

      <NotificationPopup onClose={() => setPopupOpen(false)} visible={popupOpen} />
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 13,
  },
  brand: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 7,
  },
  brandText: {
    color: colors.primary,
    fontSize: 19,
    fontWeight: '900',
    includeFontPadding: false,
    letterSpacing: -0.8,
    lineHeight: 24,
  },
  header: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    flexDirection: 'row',
    flexShrink: 0,
    height: APP_HEADER_HEIGHT,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
  },
  pressed: {
    opacity: 0.6,
  },
  profileCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderColor: colors.basaltSoft,
    borderRadius: PROFILE_SIZE / 2,
    borderWidth: 1,
    height: PROFILE_SIZE,
    justifyContent: 'center',
    overflow: 'hidden',
    width: PROFILE_SIZE,
  },
  profileImage: {
    height: '100%',
    width: '100%',
  },
  symbol: {
    height: SYMBOL_HEIGHT,
    width: SYMBOL_WIDTH,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

const navigationItems = [
  { label: '홈', icon: 'home-outline' as const, path: '/' as const },
  { label: '루트', icon: 'map-outline' as const, path: '/routes' as const },
  { label: '챗봇', icon: 'chatbubble-ellipses-outline' as const, path: '/chatbot' as const },
  { label: '내 여행', icon: 'calendar-outline' as const, path: '/trips' as const },
  { label: '마이', icon: 'person-outline' as const, path: '/profile' as const },
];

export function RouteBottomNavigation() {
  const router = useRouter();

  return (
    <View style={styles.navigation}>
      {navigationItems.map((item) => {
        const active = item.path === '/routes';
        return (
          <Pressable
            accessibilityState={{ selected: active }}
            key={item.path}
            onPress={() => router.replace(item.path)}
            style={styles.item}
          >
            <Ionicons color={active ? colors.primary : colors.textSecondary} name={item.icon} size={22} />
            <Text numberOfLines={1} style={[styles.label, active && styles.activeLabel]}>
              {item.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  navigation: { alignItems: 'center', backgroundColor: colors.surface, borderTopColor: colors.divider, borderTopWidth: 1, flexDirection: 'row', minHeight: 62, paddingBottom: 6, paddingHorizontal: 3, paddingTop: 6 },
  item: { alignItems: 'center', flex: 1, gap: 3, justifyContent: 'center', minWidth: 0 },
  label: { color: colors.textSecondary, fontSize: 9, fontWeight: '700' },
  activeLabel: { color: colors.primary, fontWeight: '900' },
});

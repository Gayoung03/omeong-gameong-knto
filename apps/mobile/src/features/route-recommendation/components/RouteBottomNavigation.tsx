import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

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
            <Ionicons color={active ? '#FF7A00' : '#777A7E'} name={item.icon} size={22} />
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
  navigation: { alignItems: 'center', backgroundColor: '#FFFFFF', borderTopColor: '#E8EAEC', borderTopWidth: 1, flexDirection: 'row', minHeight: 62, paddingBottom: 6, paddingHorizontal: 3, paddingTop: 6 },
  item: { alignItems: 'center', flex: 1, gap: 3, justifyContent: 'center', minWidth: 0 },
  label: { color: '#777A7E', fontSize: 9, fontWeight: '700' },
  activeLabel: { color: '#FF7A00', fontWeight: '900' },
});

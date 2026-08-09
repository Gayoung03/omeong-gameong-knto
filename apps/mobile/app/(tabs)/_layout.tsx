import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';

import { getAuthSession } from '@/src/features/auth/services/authStorage';
import { colors } from '@/src/theme';

const tabIcons = {
  '(home)': 'home-outline',
  routes: 'map-outline',
  chatbot: 'chatbubble-ellipses-outline',
  trips: 'calendar-outline',
  profile: 'person-outline',
} as const;

export default function TabLayout() {
  const router = useRouter();
  const [sessionChecked, setSessionChecked] = useState(false);

  useEffect(() => {
    void getAuthSession().then((session) => {
      // TODO(통합): 통합 QA 동안만 개발 모드에서 로그인 없이 탭에 접근할 수 있게 우회한다.
      //            통합 PR 올리기 전에 이 조건을 `if (!session)` 으로 반드시 되돌릴 것.
      if (!session && !__DEV__) {
        router.replace('/login');
        return;
      }
      setSessionChecked(true);
    });
  }, [router]);

  if (!sessionChecked) return null;

  return (
    <Tabs
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarIcon: ({ color, size }) => (
          <Ionicons
            color={color}
            name={tabIcons[route.name as keyof typeof tabIcons]}
            size={size}
          />
        ),
      })}
    >
      <Tabs.Screen name="(home)" options={{ title: '홈' }} />
      <Tabs.Screen name="routes" options={{ title: '루트' }} />
      <Tabs.Screen name="chatbot" options={{ title: '챗봇' }} />
      <Tabs.Screen name="trips" options={{ title: '내 여행' }} />
      <Tabs.Screen name="profile" options={{ title: '마이' }} />
    </Tabs>
  );
}

import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';

import { getAuthSession } from '@/src/features/auth/services/authStorage';
import { PushNotificationBootstrap } from '@/src/features/notifications/components/PushNotificationBootstrap';
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
      if (!session) {
        router.replace('/login');
        return;
      }
      setSessionChecked(true);
    });
  }, [router]);

  if (!sessionChecked) return null;

  return (
    <>
      <PushNotificationBootstrap />
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
    </>
  );
}

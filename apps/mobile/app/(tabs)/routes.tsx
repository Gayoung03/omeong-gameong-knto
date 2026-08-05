import { Tabs } from 'expo-router';

import { RouteInputScreen } from '@/src/features/route-recommendation/screens/RouteInputScreen';

export default function RoutesRoute() {
  return (
    <>
      <Tabs.Screen
        options={{
          tabBarStyle: {
            display: 'none',
          },
        }}
      />
      <RouteInputScreen />
    </>
  );
}

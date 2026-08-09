import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { queryClient } from '@/src/services/queryClient';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={styles.root}>
      <QueryClientProvider client={queryClient}>
        {/* TODO(통합): 인증 붙인 뒤 initialRouteName="(auth)" 복원 검토 — 현재는 (tabs)/_layout 의 세션 검사로 처리 */}
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="places/[placeId]" />
          <Stack.Screen name="routes/result" />
          <Stack.Screen name="trips/[tripId]/index" />
          <Stack.Screen name="trips/[tripId]/edit" />
          <Stack.Screen name="trips/[tripId]/info" />
          <Stack.Screen name="trips/[tripId]/add-schedule" />
        </Stack>
        <StatusBar style="auto" />
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});

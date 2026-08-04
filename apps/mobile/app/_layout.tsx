import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { queryClient } from '@/src/services/queryClient';

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="places/[placeId]" />
        <Stack.Screen name="trips/[tripId]/index" />
        <Stack.Screen name="trips/[tripId]/edit" />
        <Stack.Screen name="trips/[tripId]/info" />
      </Stack>
      <StatusBar style="auto" />
    </QueryClientProvider>
  );
}

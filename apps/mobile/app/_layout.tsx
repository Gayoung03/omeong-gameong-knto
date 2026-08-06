import { BottomSheetModalProvider } from '@gorhom/bottom-sheet';
import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { queryClient } from '@/src/services/queryClient';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <BottomSheetModalProvider>
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="(auth)" />
            <Stack.Screen name="places/[placeId]" />
            <Stack.Screen name="trips/[tripId]/index" />
            <Stack.Screen name="trips/[tripId]/edit" />
            <Stack.Screen name="travel-logs/index" />
            <Stack.Screen name="travel-logs/[tripId]" />
            <Stack.Screen name="travel-logs/new-moment/index" />
            <Stack.Screen name="travel-logs/new-moment/details" />
            <Stack.Screen name="travel-logs/new-moment/style" />
            <Stack.Screen name="travel-logs/new-moment/generating" options={{ gestureEnabled: false }} />
            <Stack.Screen name="travel-logs/new-moment/complete" options={{ gestureEnabled: false }} />
            <Stack.Screen name="notices" />
            <Stack.Screen name="notification-settings" />
            <Stack.Screen name="account-withdraw" />
            <Stack.Screen name="inquiries/index" />
            <Stack.Screen name="inquiries/new" />
            <Stack.Screen name="inquiries/[inquiryId]" />
            <Stack.Screen name="settings" options={{ presentation: 'modal' }} />
            <Stack.Screen name="profile-edit" options={{ presentation: 'modal' }} />
            <Stack.Screen name="pets/new" options={{ presentation: 'modal' }} />
            <Stack.Screen name="pets/[petId]" options={{ presentation: 'modal' }} />
          </Stack>
          <StatusBar style="auto" />
        </BottomSheetModalProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

import { BottomSheetModalProvider } from '@gorhom/bottom-sheet';
import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { AppErrorBoundary } from '@/src/components/feedback/AppErrorBoundary';
import { queryClient } from '@/src/services/queryClient';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={styles.root}>
      <AppErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <BottomSheetModalProvider>
            {/* TODO(통합): 인증 붙인 뒤 initialRouteName="(auth)" 복원 검토 — 현재는 (tabs)/_layout 의 세션 검사로 처리 */}
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="(tabs)" />
              <Stack.Screen name="(auth)" />

              <Stack.Screen name="places/[placeId]" />
            <Stack.Screen name="places/[placeId]/reviews/index" />
            <Stack.Screen name="places/[placeId]/reviews/new" />
            <Stack.Screen name="places/[placeId]/reviews/[reviewId]/edit" />
            <Stack.Screen name="reviews/my" />
              <Stack.Screen name="stories/[storyId]" />

              <Stack.Screen name="trips/[tripId]/index" />
              <Stack.Screen name="trips/[tripId]/edit" />
              <Stack.Screen name="trips/[tripId]/info" />
              <Stack.Screen name="trips/[tripId]/add-schedule" />

              <Stack.Screen name="travel-logs/index" />
              <Stack.Screen name="travel-logs/[tripId]" />
              <Stack.Screen name="travel-logs/new-moment/index" />
              <Stack.Screen name="travel-logs/new-moment/details" />
              <Stack.Screen name="travel-logs/new-moment/style" />
              <Stack.Screen
                name="travel-logs/new-moment/generating"
                options={{ gestureEnabled: false }}
              />
              <Stack.Screen
                name="travel-logs/new-moment/complete"
                options={{ gestureEnabled: false }}
              />

              <Stack.Screen name="travel-guides/preparation" />

              <Stack.Screen name="saved/places" />
              <Stack.Screen name="saved/routes" />

              <Stack.Screen name="notifications" />
              <Stack.Screen name="notices" />
              <Stack.Screen name="notification-settings" />
              <Stack.Screen name="account-withdraw" />
              <Stack.Screen name="inquiries/index" />
              <Stack.Screen name="inquiries/new" />
              <Stack.Screen name="inquiries/[inquiryId]" />

              <Stack.Screen name="legal/terms" />
              <Stack.Screen name="legal/privacy" />

              <Stack.Screen name="settings" options={{ presentation: 'modal' }} />
              <Stack.Screen name="profile-edit" options={{ presentation: 'modal' }} />
              <Stack.Screen name="pets/new" options={{ presentation: 'modal' }} />
              <Stack.Screen name="pets/[petId]" options={{ presentation: 'modal' }} />
            </Stack>
            <StatusBar style="auto" />
          </BottomSheetModalProvider>
        </QueryClientProvider>
      </AppErrorBoundary>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});

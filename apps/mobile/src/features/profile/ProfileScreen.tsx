import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppHeader } from '@/src/components/layout/AppHeader';
import { ScreenTitleBar } from '@/src/components/layout/ScreenTitleBar';
import { IconButton } from '@/src/components/ui/IconButton';
import { SectionHeader } from '@/src/components/ui/SectionHeader';
import { colors, spacing } from '@/src/theme';

import { PetProfileSection } from './components/PetProfileSection';
import { ProfileFooterLinks } from './components/ProfileFooterLinks';
import { TravelSummarySection } from './components/TravelSummarySection';
import { UserProfileSection } from './components/UserProfileSection';
import { usePets } from './hooks/usePets';
import { useUserProfile } from './hooks/useUserProfile';
import { mockActivitySummary } from './mocks/profile.mock';

export function ProfileScreen() {
  const router = useRouter();
  const { data: user } = useUserProfile();
  // 지워진 프로필은 이 목록에 오지 않는다.
  const { data: pets = [] } = usePets();

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <AppHeader />
      <ScreenTitleBar
        right={
          <IconButton
            accessibilityLabel="설정"
            icon="settings-outline"
            onPress={() => router.push('/settings')}
          />
        }
        title="마이페이지"
      />
      <ScrollView contentContainerStyle={styles.content} style={styles.scrollView}>
        {/* 메뉴 바만 화면 너비를 꽉 채워야 해서 좌우 여백은 이 래퍼가 갖는다. */}
        <View style={styles.sections}>
          {user && <UserProfileSection user={user} />}

          <SectionHeader
            actionLabel="+ 등록"
            onActionPress={() => router.push('/pets/new')}
            title="나의 반려동물"
          />
          <PetProfileSection pets={pets} />

          <SectionHeader title="나의 여행" />
          <TravelSummarySection summary={mockActivitySummary} />
        </View>

        <ProfileFooterLinks />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.xl,
    paddingTop: spacing.md,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  sections: {
    gap: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  scrollView: {
    flex: 1,
  },
});

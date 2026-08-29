import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Image, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/src/components/layout/AppHeader';
import { brandAssets } from '@/src/config/brandAssets';
import { colors, radius, spacing } from '@/src/theme';

const GUIDE_ITEMS = [
  {
    icon: 'paw-outline' as const,
    title: '우리 아이에게 맞게',
    description: '반려동물의 종류와 크기, 동반 조건을 함께 살펴봐요.',
  },
  {
    icon: 'heart-outline' as const,
    title: '이번 여행의 취향에 맞게',
    description: '가고 싶은 장소와 중요한 기준을 추천에 반영해요.',
  },
  {
    icon: 'map-outline' as const,
    title: '이동이 부담스럽지 않게',
    description: '일정과 숙소를 기준으로 제주 여행 코스를 정리해요.',
  },
];

export function RouteIntroScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.screen}>
        <AppHeader notifications="popup" />

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            <View style={styles.hero}>
              <View style={styles.eyebrowBadge}>
                <Ionicons color={colors.primary} name="sparkles" size={13} />
                <Text style={styles.eyebrowText}>혼디와 만드는 제주 여행</Text>
              </View>

              <Text style={styles.heroTitle}>
                우리 아이와 함께할{`\n`}
                <Text style={styles.heroTitleAccent}>제주 루트</Text>를 찾아드릴게요!
              </Text>
              <Text style={styles.heroDescription}>
                여행 일정과 취향을 알려주면{`\n`}
                혼디가 우리 아이에게 맞는 코스를 차근차근 찾아볼게요.
              </Text>

              <View style={styles.mascotFrame}>
                <View style={styles.mascotGlow} />
                <Image
                  accessibilityLabel="제주 지도를 보며 루트를 찾는 혼디"
                  resizeMode="contain"
                  source={brandAssets.character.map}
                  style={styles.mascot}
                />
              </View>
            </View>

            <View style={styles.guideCard}>
              <Text style={styles.guideTitle}>혼디가 이렇게 도와드려요</Text>
              <View style={styles.guideList}>
                {GUIDE_ITEMS.map((item) => (
                  <View key={item.title} style={styles.guideRow}>
                    <View style={styles.guideIcon}>
                      <Ionicons color={colors.primary} name={item.icon} size={19} />
                    </View>
                    <View style={styles.guideCopy}>
                      <Text style={styles.guideItemTitle}>{item.title}</Text>
                      <Text style={styles.guideItemDescription}>{item.description}</Text>
                    </View>
                  </View>
                ))}
              </View>
            </View>

            <Pressable
              accessibilityHint="루트 추천을 위한 정보 입력을 시작합니다"
              accessibilityRole="button"
              onPress={() => router.push('/routes/input')}
              style={({ pressed }) => [styles.startButton, pressed && styles.pressed]}
            >
              <Text style={styles.startButtonText}>나만의 제주 루트 만들기</Text>
              <Ionicons color={colors.surface} name="arrow-forward" size={19} />
            </Pressable>
            <Text style={styles.helperText}>입력한 내용은 자동으로 저장돼요.</Text>
          </View>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  screen: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: spacing.xl },
  content: {
    alignSelf: 'center',
    maxWidth: 720,
    paddingHorizontal: spacing.md,
    width: '100%',
  },
  hero: { alignItems: 'center', paddingTop: spacing.lg },
  eyebrowBadge: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: 5,
    paddingHorizontal: 11,
    paddingVertical: 6,
  },
  eyebrowText: { color: colors.primary, fontSize: 11, fontWeight: '800' },
  heroTitle: {
    color: colors.textPrimary,
    fontSize: 25,
    fontWeight: '900',
    letterSpacing: -1,
    lineHeight: 35,
    marginTop: 15,
    textAlign: 'center',
  },
  heroTitleAccent: { color: colors.primary },
  heroDescription: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 20,
    marginTop: 9,
    textAlign: 'center',
  },
  mascotFrame: {
    alignItems: 'center',
    height: 225,
    justifyContent: 'center',
    marginTop: 4,
    position: 'relative',
    width: '100%',
  },
  mascotGlow: {
    backgroundColor: colors.primarySoft,
    borderRadius: 90,
    height: 176,
    position: 'absolute',
    width: 176,
  },
  mascot: { height: '100%', width: '100%' },
  guideCard: {
    backgroundColor: colors.surface,
    borderColor: colors.basaltSoft,
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing.md,
    shadowColor: colors.primaryInk,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
  },
  guideTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '800' },
  guideList: { gap: 14, marginTop: 15 },
  guideRow: { alignItems: 'center', flexDirection: 'row', gap: 11 },
  guideIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: 13,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  guideCopy: { flex: 1 },
  guideItemTitle: { color: colors.textStrong, fontSize: 13, fontWeight: '800' },
  guideItemDescription: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 2,
  },
  startButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
    marginTop: spacing.lg,
    minHeight: 56,
    paddingHorizontal: spacing.md,
  },
  startButtonText: { color: colors.surface, fontSize: 15, fontWeight: '900' },
  helperText: {
    color: colors.textTertiary,
    fontSize: 10,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  pressed: { opacity: 0.7 },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { usePets } from '@/src/features/profile/hooks/usePets';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';
import type { MomentMood, WritingStyle } from '@/src/types/logDraft';

import { useLogDraftStore } from './stores/useLogDraftStore';

const STYLE_LABELS: Record<WritingStyle, string> = {
  dog_diary: '강아지 일기',
  jeju_dialect: '제주 방언',
};
const MOOD_LABELS: Record<MomentMood, string> = {
  happy: '행복했수다',
  excited: '신났댕',
  relaxed: '여유로웠개',
  bittersweet: '조금 아쉬웠개',
};

export function NewMomentGeneratingScreen() {
  const router = useRouter();
  const draft = useLogDraftStore((state) => state.draft);
  const status = useLogDraftStore((state) => state.generationStatus);
  const errorMessage = useLogDraftStore((state) => state.errorMessage);
  const startGeneration = useLogDraftStore((state) => state.startGeneration);
  const { data: activePets = [] } = usePets();
  const petNames = activePets
    .filter((pet) => draft.petIds.includes(pet.petId))
    .map((pet) => pet.name)
    .join(' · ');

  useEffect(() => {
    if (status === 'completed') router.replace('/travel-logs/new-moment/complete');
  }, [router, status]);

  if (status === 'failed') {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.failedContent}>
          <Ionicons color={colors.error} name="alert-circle-outline" size={52} />
          <Text style={styles.title}>여행 기록을 만들지 못했어요</Text>
          <Text style={styles.subtitle}>{errorMessage}</Text>
          <Pressable onPress={() => void startGeneration()} style={styles.primaryButton}>
            <Text style={styles.primaryLabel}>다시 시도</Text>
          </Pressable>
          <Pressable onPress={() => router.replace('/travel-logs/new-moment/style')} style={styles.outlineButton}>
            <Text style={styles.outlineLabel}>이전 단계로 돌아가기</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const uploading = status === 'uploading';
  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <View style={styles.content}>
        <Text style={styles.title}>{uploading ? '사진을 준비하고 있어요' : '여행의 순간을 기록하고 있어요'}</Text>
        <View style={styles.photoFrame}>
          <RemoteImage borderRadius={radius.md} style={styles.photo} uri={draft.localPhotoUri ?? undefined} />
        </View>
        <View style={styles.loaderDecoration}>
          <View style={styles.smallDot} />
          <Ionicons color={colors.primary} name="paw" size={38} />
          <View style={styles.smallDot} />
        </View>
        <Text style={styles.title}>{uploading ? '선택한 사진을 확인하는 중이에요' : `${STYLE_LABELS[draft.writingStyle]} 스타일로 꾸미는 중이에요`}</Text>
        <Text style={styles.subtitle}>잠시만 기다려 주세요</Text>
        <View style={styles.chips}>
          <SummaryChip icon="calendar-outline" label={draft.recordedDate?.replaceAll('-', '.') ?? ''} />
          <SummaryChip icon="location-outline" label={draft.placeName ?? ''} />
          <SummaryChip icon="paw-outline" label={petNames} />
          {draft.mood ? <SummaryChip icon="happy-outline" label={MOOD_LABELS[draft.mood]} /> : null}
        </View>
        <View style={styles.steps}>
          <Text style={[styles.step, styles.stepDone]}>사진 준비</Text>
          <View style={[styles.line, uploading ? undefined : styles.lineDone]} />
          <Text style={[styles.step, !uploading && styles.stepActive]}>로그 생성</Text>
          <View style={styles.line} />
          <Text style={styles.step}>앨범 저장</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

function SummaryChip({ icon, label }: { icon: keyof typeof Ionicons.glyphMap; label: string }) {
  return (
    <View style={styles.chip}>
      <Ionicons color={colors.iconGray} name={icon} size={15} />
      <Text numberOfLines={1} style={styles.chipLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { alignItems: 'center', borderColor: colors.border, borderRadius: radius.sm, borderWidth: 1, flexDirection: 'row', gap: spacing.xs, paddingHorizontal: spacing.sm, paddingVertical: 7 },
  chipLabel: { color: colors.textSecondary, fontSize: 11, maxWidth: 105 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, justifyContent: 'center' },
  content: { alignItems: 'center', flex: 1, gap: spacing.md, justifyContent: 'center', padding: spacing.lg },
  failedContent: { alignItems: 'center', flex: 1, gap: spacing.md, justifyContent: 'center', padding: spacing.xl },
  line: { backgroundColor: colors.border, height: 2, width: 34 },
  lineDone: { backgroundColor: colors.primary },
  loaderDecoration: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  outlineButton: { alignItems: 'center', borderColor: colors.secondary, borderRadius: radius.sm, borderWidth: 1, maxWidth: 340, padding: spacing.md, width: '100%' },
  outlineLabel: { color: colors.secondary, fontWeight: '700' },
  photo: { height: 330, width: 330 },
  photoFrame: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.sm, shadowColor: overlayColors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 6 },
  primaryButton: { alignItems: 'center', backgroundColor: colors.primary, borderRadius: radius.sm, maxWidth: 340, padding: spacing.md, width: '100%' },
  primaryLabel: { color: colors.surface, fontWeight: '700' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  smallDot: { backgroundColor: colors.primarySoft, borderRadius: 4, height: 8, width: 8 },
  step: { color: colors.textSecondary, fontSize: 11 },
  stepActive: { color: colors.primary, fontWeight: '700' },
  stepDone: { color: colors.secondary, fontWeight: '700' },
  steps: { alignItems: 'center', flexDirection: 'row', marginTop: spacing.sm },
  subtitle: { color: colors.textSecondary, fontSize: 13, textAlign: 'center' },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize, fontWeight: '700', textAlign: 'center' },
});

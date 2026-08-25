import Ionicons from '@expo/vector-icons/Ionicons';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, Share, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import { MemoryFlipCard } from './components/MemoryFlipCard';
import { travelLogQueryKey } from './hooks/useTravelLogItems';
import { useLogDraftStore } from './stores/useLogDraftStore';

export function NewMomentCompleteScreen() {
  const router = useRouter();
  const generatedLog = useLogDraftStore((state) => state.generatedLog);
  const resetDraft = useLogDraftStore((state) => state.resetDraft);
  const regenerate = useLogDraftStore((state) => state.regenerate);
  const queryClient = useQueryClient();
  const [isSaving, setIsSaving] = useState(false);
  const [isFlipped, setIsFlipped] = useState(false);

  if (!generatedLog) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.missingState}>
          <Text style={styles.subtitle}>완성된 여행 기록을 찾을 수 없어요.</Text>
          <Pressable onPress={() => router.replace('/travel-logs/new-moment/style')} style={styles.outlineButton}>
            <Text style={styles.outlineLabel}>이전 단계로 돌아가기</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // 같은 기록의 이미지만 새로 만든다. startGeneration 을 다시 부르면
  // 기록이 하나 더 생긴다.
  const remake = () => {
    void regenerate();
    router.replace('/travel-logs/new-moment/generating');
  };
  const share = () => {
    Share.share({ message: generatedLog.generatedImageUrl, title: '오멍가멍 여행 기록', url: generatedLog.generatedImageUrl }).catch(() => {});
  };
  /**
   * 기록은 만들어진 시점에 이미 서버에 저장돼 있다. 여기서는 목록이 새 기록을
   * 알아보도록 캐시를 비우고 목록으로 돌아갈 뿐이다.
   */
  const save = async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      await queryClient.invalidateQueries({ queryKey: travelLogQueryKey });
      resetDraft();
      router.dismissTo('/travel-logs');
    } catch {
      setIsSaving(false);
      Alert.alert('목록을 새로 불러오지 못했어요', '기록은 저장돼 있어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <View style={styles.content}>
        <View style={styles.completeHeading}>
          <Text style={styles.title}>또 하나의 추억이 완성됐어요</Text>
          <Ionicons color={colors.secondary} name="sparkles-outline" size={24} />
        </View>
        <View style={styles.memoryCard}>
          {/* 저장 전이라 뒷면의 한 줄 기록 수정은 아직 지원하지 않는다(수정 대상 logId가 없음). */}
          <MemoryFlipCard aspectRatio={0.86} log={generatedLog} onFlipChange={setIsFlipped} />
        </View>
        <View style={styles.flipHint}>
          <Ionicons color={colors.iconGray} name="hand-left-outline" size={18} />
          <Text style={styles.subtitle}>
            {isFlipped ? '카드를 누르면 사진으로 돌아가요' : '사진을 누르면 뒷면의 기록을 볼 수 있어요'}
          </Text>
        </View>
        <View style={styles.actions}>
          <Pressable onPress={remake} style={styles.outlineButton}>
            <Ionicons color={colors.secondary} name="refresh-outline" size={19} />
            <Text style={styles.outlineLabel}>다시 만들기</Text>
          </Pressable>
          <Pressable onPress={share} style={styles.outlineButton}>
            <Ionicons color={colors.secondary} name="share-social-outline" size={19} />
            <Text style={styles.outlineLabel}>공유하기</Text>
          </Pressable>
        </View>
      </View>
      <View style={styles.footer}>
        <Pressable disabled={isSaving} onPress={() => void save()} style={[styles.saveButton, isSaving && styles.saveDisabled]}>
          <Ionicons color={colors.surface} name="download-outline" size={21} />
          {/* 저장은 이미 끝났다. 이 버튼은 목록으로 돌아가는 길이다. */}
          <Text style={styles.saveLabel}>{isSaving ? '불러오는 중...' : '기록 목록에서 보기'}</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: spacing.sm, width: '100%' },
  completeHeading: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  content: { alignItems: 'center', flex: 1, gap: spacing.md, justifyContent: 'center', padding: spacing.lg },
  flipHint: { alignItems: 'center', flexDirection: 'row', gap: spacing.xs },
  footer: { padding: spacing.md },
  memoryCard: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, maxWidth: 390, padding: spacing.md, shadowColor: overlayColors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.09, shadowRadius: 6, width: '100%' },
  missingState: { alignItems: 'center', flex: 1, gap: spacing.md, justifyContent: 'center', padding: spacing.lg },
  outlineButton: { alignItems: 'center', borderColor: colors.secondary, borderRadius: radius.sm, borderWidth: 1, flex: 1, flexDirection: 'row', gap: spacing.xs, justifyContent: 'center', padding: spacing.md },
  outlineLabel: { color: colors.secondary, fontWeight: '600' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  saveButton: { alignItems: 'center', backgroundColor: colors.primary, borderRadius: radius.sm, flexDirection: 'row', gap: spacing.sm, justifyContent: 'center', padding: 15 },
  saveDisabled: { opacity: 0.65 },
  saveLabel: { color: colors.surface, fontSize: typography.body.fontSize, fontWeight: '700' },
  subtitle: { color: colors.textSecondary, fontSize: 13, textAlign: 'center' },
  title: { color: colors.textPrimary, fontSize: 18, fontWeight: '700' },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Avatar } from '@/src/components/ui/Avatar';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { usePets } from '@/src/features/profile/hooks/usePets';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { MomentMood, WritingStyle } from '@/src/types/logDraft';

import { MomentStepHeader } from './components/MomentStepHeader';
import { useLogDraftStore } from './stores/useLogDraftStore';

const STYLE_OPTIONS: {
  value: WritingStyle;
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
}[] = [
  { value: 'dog_diary', title: '강아지 일기', subtitle: '귀여운 강아지 말투', icon: 'paw-outline' },
  {
    value: 'jeju_dialect',
    title: '제주 방언',
    subtitle: '제주어로 남기는 여행 기록',
    icon: 'water-outline',
  },
];
const MOOD_OPTIONS: { value: MomentMood; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: 'happy', label: '행복했수다', icon: 'happy-outline' },
  { value: 'excited', label: '신났댕', icon: 'sparkles-outline' },
  { value: 'relaxed', label: '여유로웠개', icon: 'cafe-outline' },
  { value: 'bittersweet', label: '조금 아쉬웠개', icon: 'sad-outline' },
];

export function NewMomentStyleStepScreen() {
  const router = useRouter();
  const draft = useLogDraftStore((state) => state.draft);
  const updateDraft = useLogDraftStore((state) => state.updateDraft);
  const startGeneration = useLogDraftStore((state) => state.startGeneration);
  const generationStatus = useLogDraftStore((state) => state.generationStatus);
  const { data: activePets = [] } = usePets();
  const pets = activePets.filter((pet) => draft.petIds.includes(pet.petId));
  const isProcessing = generationStatus === 'uploading' || generationStatus === 'generating';
  const canSubmit = Boolean(
    draft.localPhotoUri &&
    draft.recordedDate &&
    draft.placeName &&
    draft.petIds.length > 0 &&
    draft.writingStyle &&
    draft.mood &&
    !isProcessing,
  );

  const generate = () => {
    if (!canSubmit) return;
    void startGeneration();
    router.push('/travel-logs/new-moment/generating');
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.safeArea}
      >
        <MomentStepHeader onBack={() => router.back()} step={3} title="이 순간을 기록해 주세요" />
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.summaryCard}>
            <RemoteImage
              borderRadius={radius.md}
              style={styles.summaryImage}
              uri={draft.localPhotoUri ?? undefined}
            />
            <View style={styles.summaryInfo}>
              <Text style={styles.summaryTitle}>
                {draft.recordedDate?.replaceAll('-', '.')} · {draft.placeName}
              </Text>
              <View style={styles.summaryPets}>
                {pets.map((pet) => (
                  <View key={pet.petId} style={styles.summaryPet}>
                    <Avatar fallbackIcon="paw" size={28} uri={pet.profileImage} />
                    <Text style={styles.petName}>{pet.name}</Text>
                  </View>
                ))}
              </View>
            </View>
            <Pressable onPress={() => router.back()} style={styles.editButton}>
              <Text style={styles.editLabel}>정보 수정</Text>
            </Pressable>
          </View>

          <Text style={styles.sectionTitle}>글 스타일</Text>
          <View style={styles.optionGrid}>
            {STYLE_OPTIONS.map((option) => {
              const selected = draft.writingStyle === option.value;
              return (
                <Pressable
                  key={option.value}
                  onPress={() => updateDraft({ writingStyle: option.value })}
                  style={[styles.styleCard, selected && styles.selectedCard]}
                >
                  {selected ? (
                    <Ionicons
                      color={colors.primary}
                      name="checkmark-circle"
                      size={20}
                      style={styles.checkIcon}
                    />
                  ) : null}
                  <Ionicons
                    color={selected ? colors.primary : colors.secondary}
                    name={option.icon}
                    size={34}
                  />
                  <Text style={styles.styleTitle}>{option.title}</Text>
                  <Text style={styles.styleSubtitle}>{option.subtitle}</Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={styles.sectionTitle}>이 순간은 어떤 느낌이었나요?</Text>
          <View style={styles.moodGrid}>
            {MOOD_OPTIONS.map((option) => {
              const selected = draft.mood === option.value;
              return (
                <Pressable
                  key={option.value}
                  onPress={() => updateDraft({ mood: option.value })}
                  style={[styles.moodButton, selected && styles.selectedCard]}
                >
                  <Ionicons
                    color={selected ? colors.primary : colors.iconGray}
                    name={option.icon}
                    size={21}
                  />
                  <Text style={[styles.moodLabel, selected && styles.selectedLabel]}>
                    {option.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={styles.sectionTitle}>나의 한 줄 (선택)</Text>
          <View style={styles.messageBox}>
            <TextInput
              maxLength={80}
              multiline
              onChangeText={(personalMessage) => updateDraft({ personalMessage })}
              placeholder="이 순간에 남기고 싶은 한마디를 적어주세요"
              placeholderTextColor={colors.textSecondary}
              style={styles.input}
              value={draft.personalMessage}
            />
            <View style={styles.messageMeta}>
              <Text style={styles.helper}>완성된 사진을 뒤집었을 때 표시돼요</Text>
              <Text style={styles.counter}>{draft.personalMessage.length} / 80</Text>
            </View>
          </View>
        </ScrollView>
        <View style={styles.footer}>
          <Pressable
            disabled={!canSubmit}
            onPress={generate}
            style={[styles.submitButton, !canSubmit && styles.submitDisabled]}
          >
            <Text style={[styles.submitLabel, !canSubmit && styles.submitLabelDisabled]}>
              이 순간 기록하기
            </Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  checkIcon: { position: 'absolute', right: spacing.sm, top: spacing.sm },
  content: { gap: spacing.sm, paddingBottom: spacing.md, paddingHorizontal: spacing.md },
  counter: { color: colors.textSecondary, fontSize: 12 },
  editButton: {
    borderColor: colors.secondary,
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: 7,
  },
  editLabel: { color: colors.secondary, fontSize: 12, fontWeight: '600' },
  footer: { borderTopColor: colors.border, borderTopWidth: 1, padding: spacing.md },
  helper: { color: colors.textSecondary, flex: 1, fontSize: 11 },
  input: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: 14,
    minHeight: 76,
    textAlignVertical: 'top',
  },
  messageBox: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 112,
    padding: spacing.sm,
  },
  messageMeta: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  moodButton: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexBasis: '48%',
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
  moodGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  moodLabel: { color: colors.textSecondary, fontSize: 13, fontWeight: '600' },
  optionGrid: { flexDirection: 'row', gap: spacing.sm },
  petName: { color: colors.textPrimary, fontSize: 13, fontWeight: '600' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: '700',
    marginTop: spacing.sm,
  },
  selectedCard: { backgroundColor: colors.primarySoft, borderColor: colors.primary },
  selectedLabel: { color: colors.primary },
  styleCard: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    minHeight: 126,
    padding: spacing.md,
  },
  styleSubtitle: { color: colors.textSecondary, fontSize: 11, marginTop: 2, textAlign: 'center' },
  styleTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '700', marginTop: spacing.xs },
  submitButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.sm,
    paddingVertical: 14,
  },
  submitDisabled: { backgroundColor: colors.neutralGray },
  submitLabel: { color: colors.surface, fontSize: typography.body.fontSize, fontWeight: '700' },
  submitLabelDisabled: { color: colors.textSecondary },
  summaryCard: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
  summaryImage: { height: 78, width: 78 },
  summaryInfo: { flex: 1, gap: spacing.sm },
  summaryPet: { alignItems: 'center', flexDirection: 'row', gap: spacing.xs },
  summaryPets: { flexDirection: 'row', gap: spacing.sm },
  summaryTitle: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
});

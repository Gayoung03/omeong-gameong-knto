import Ionicons from '@expo/vector-icons/Ionicons';
import * as ImagePicker from 'expo-image-picker';
import { useNavigation, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Keyboard,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/src/components/ui/Button';
import { LabeledField } from '@/src/components/ui/LabeledField';
import { PhotoPicker } from '@/src/components/ui/PhotoPicker';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { DiscardChangesModal } from '@/src/features/profile/components/DiscardChangesModal';
import { SaveCompleteModal } from '@/src/features/profile/components/SaveCompleteModal';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { InquiryCategory } from '@/src/types/inquiry';

import {
  InquiryCategorySheet,
  type InquiryCategorySheetHandle,
} from './components/InquiryCategorySheet';
import { useCreateInquiry } from './hooks/useCreateInquiry';

const MAX_INQUIRY_IMAGES = 3;
const MAX_TITLE_LENGTH = 50;
const MAX_CONTENT_LENGTH = 1000;

function showPermissionAlert() {
  Alert.alert(
    '사진 앨범 권한이 필요해요',
    '문의에 사진을 첨부하려면 설정에서 사진 앨범 접근을 허용해 주세요.',
    [
      { text: '취소', style: 'cancel' },
      { text: '설정 열기', onPress: () => Linking.openSettings() },
    ],
  );
}

export function InquiryCreateScreen() {
  const router = useRouter();
  const navigation = useNavigation();
  const createMutation = useCreateInquiry();

  const [category, setCategory] = useState<InquiryCategory>();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [imageUris, setImageUris] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>();
  const [discardModalVisible, setDiscardModalVisible] = useState(false);
  const [completeModalVisible, setCompleteModalVisible] = useState(false);

  const categorySheetRef = useRef<InquiryCategorySheetHandle>(null);
  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);

  const isSaving = createMutation.isPending;
  const isDirty = Boolean(category || title || content || imageUris.length > 0);
  // 유형·제목·내용 세 가지가 필수값이다.
  const isSubmitDisabled = !category || !title.trim() || !content.trim() || isSaving;

  useEffect(() => {
    return navigation.addListener('beforeRemove', (event) => {
      if (allowExitRef.current || !isDirty) return;

      event.preventDefault();
      if (exitModalOpenRef.current) return;
      exitModalOpenRef.current = true;
      pendingExitRef.current = () => navigation.dispatch(event.data.action);
      setDiscardModalVisible(true);
    });
  }, [isDirty, navigation]);

  const addPhotos = async () => {
    const remaining = MAX_INQUIRY_IMAGES - imageUris.length;
    if (remaining <= 0) return;

    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        showPermissionAlert();
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        allowsMultipleSelection: remaining > 1,
        mediaTypes: ['images'],
        quality: 0.9,
        selectionLimit: remaining,
      });
      if (!result.canceled) {
        const picked = result.assets.map((asset) => asset.uri);
        // 같은 사진을 두 번 고르면 썸네일 key가 겹치므로 중복은 걸러낸다.
        setImageUris((current) => [
          ...current,
          ...picked.filter((uri) => !current.includes(uri)),
        ].slice(0, MAX_INQUIRY_IMAGES));
        setErrorMessage(undefined);
      }
    } catch {
      setErrorMessage('사진 앨범을 열 수 없어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  const removePhoto = (uri: string) => {
    setImageUris((current) => current.filter((item) => item !== uri));
  };

  const handleSubmit = () => {
    Keyboard.dismiss();
    if (isSubmitDisabled || !category) return;

    createMutation.mutate(
      { category, title, content, localImageUris: imageUris },
      {
        onSuccess: () => {
          setErrorMessage(undefined);
          setCompleteModalVisible(true);
        },
        onError: () => setErrorMessage('문의를 등록하지 못했어요. 잠시 후 다시 시도해 주세요.'),
      },
    );
  };

  const continueEditing = () => {
    exitModalOpenRef.current = false;
    pendingExitRef.current = null;
    setDiscardModalVisible(false);
  };

  const discardChanges = () => {
    const exit = pendingExitRef.current;
    allowExitRef.current = true;
    exitModalOpenRef.current = false;
    pendingExitRef.current = null;
    setDiscardModalVisible(false);
    exit?.();
  };

  const closeComplete = () => {
    setCompleteModalVisible(false);
    allowExitRef.current = true;
    router.back();
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="문의 작성" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <LabeledField label="문의 유형">
            <Pressable
              accessibilityRole="button"
              disabled={isSaving}
              onPress={() => categorySheetRef.current?.open()}
              style={styles.select}
            >
              <Text style={[styles.selectLabel, !category && styles.selectPlaceholder]}>
                {category ?? '문의 유형을 선택해주세요'}
              </Text>
              <Ionicons color={colors.textSecondary} name="chevron-down" size={18} />
            </Pressable>
          </LabeledField>

          <LabeledField label="제목">
            <TextInput
              editable={!isSaving}
              maxLength={MAX_TITLE_LENGTH}
              onChangeText={(text) => setTitle(text.replace(/\n/g, ''))}
              placeholder="문의 제목을 입력해주세요"
              placeholderTextColor={colors.textSecondary}
              style={styles.input}
              value={title}
            />
          </LabeledField>

          <LabeledField label="문의 내용">
            <View style={styles.textAreaBox}>
              <TextInput
                editable={!isSaving}
                maxLength={MAX_CONTENT_LENGTH}
                multiline
                onChangeText={setContent}
                placeholder="문의 내용을 자세히 입력해주세요."
                placeholderTextColor={colors.textSecondary}
                style={styles.textArea}
                textAlignVertical="top"
                value={content}
              />
              <Text style={styles.counter}>
                {content.length}/{MAX_CONTENT_LENGTH}
              </Text>
            </View>
          </LabeledField>

          <LabeledField label="사진 첨부">
            <PhotoPicker
              disabled={isSaving}
              imageUris={imageUris}
              maxImages={MAX_INQUIRY_IMAGES}
              onAdd={() => void addPhotos()}
              onRemove={removePhoto}
            />
          </LabeledField>

          <View style={styles.infoRow}>
            <Ionicons color={colors.sea} name="information-circle-outline" size={16} />
            <Text style={styles.infoText}>답변이 등록되면 앱에서 확인할 수 있어요.</Text>
          </View>

          {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}
        </ScrollView>

        <View style={styles.footer}>
          <Button
            disabled={isSubmitDisabled}
            label={isSaving ? '등록 중...' : '문의 등록'}
            onPress={handleSubmit}
            size="md"
            variant="primary"
          />
        </View>
      </KeyboardAvoidingView>

      <InquiryCategorySheet onSelect={setCategory} ref={categorySheetRef} value={category} />
      <DiscardChangesModal
        description="작성한 문의 내용이 저장되지 않아요."
        onContinue={continueEditing}
        onDiscard={discardChanges}
        visible={discardModalVisible}
      />
      <SaveCompleteModal
        description="확인 후 답변해드릴게요."
        onConfirm={closeComplete}
        title="문의가 등록되었어요"
        visible={completeModalVisible}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  counter: {
    alignSelf: 'flex-end',
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 4,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  flex: {
    flex: 1,
  },
  footer: {
    backgroundColor: colors.background,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  infoRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  infoText: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  input: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    minHeight: 48,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  mutationError: {
    color: colors.error,
    fontSize: 13,
    textAlign: 'center',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  select: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 48,
    paddingHorizontal: spacing.md,
  },
  selectLabel: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
  },
  selectPlaceholder: {
    color: colors.textSecondary,
  },
  textArea: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    lineHeight: 22,
    minHeight: 150,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  textAreaBox: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
  },
});

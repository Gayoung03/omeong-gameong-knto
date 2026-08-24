import { useNavigation, useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
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

import { StarRating } from '../components/StarRating';
import { useCreateReview } from '../hooks/useCreateReview';
import { REVIEW_CONTENT_MAX_LENGTH, REVIEW_PHOTO_MAX_COUNT } from '../types/review';

type ReviewCreateScreenProps = {
  placeId: string;
};

function showPermissionAlert() {
  Alert.alert(
    '사진 앨범 권한이 필요해요',
    '리뷰에 사진을 첨부하려면 설정에서 사진 앨범 접근을 허용해 주세요.',
    [
      { text: '취소', style: 'cancel' },
      { text: '설정 열기', onPress: () => Linking.openSettings() },
    ],
  );
}

export function ReviewCreateScreen({ placeId }: ReviewCreateScreenProps) {
  const router = useRouter();
  const navigation = useNavigation();
  const createMutation = useCreateReview();

  const [rating, setRating] = useState(0);
  const [content, setContent] = useState('');
  const [photoUris, setPhotoUris] = useState<string[]>([]);
  const [petPolicyAccurate, setPetPolicyAccurate] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>();
  const [discardModalVisible, setDiscardModalVisible] = useState(false);
  const [completeModalVisible, setCompleteModalVisible] = useState(false);

  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);

  const isSaving = createMutation.isPending;
  const isDirty = Boolean(rating || content || photoUris.length > 0 || petPolicyAccurate !== null);
  // 별점·내용 두 가지가 필수값이다.
  const isSubmitDisabled = rating === 0 || !content.trim() || isSaving;

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
    const remaining = REVIEW_PHOTO_MAX_COUNT - photoUris.length;
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
        setPhotoUris((current) =>
          [...current, ...picked.filter((uri) => !current.includes(uri))].slice(
            0,
            REVIEW_PHOTO_MAX_COUNT,
          ),
        );
        setErrorMessage(undefined);
      }
    } catch {
      setErrorMessage('사진 앨범을 열 수 없어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  const removePhoto = (uri: string) => {
    setPhotoUris((current) => current.filter((item) => item !== uri));
  };

  const handleSubmit = () => {
    Keyboard.dismiss();
    if (isSubmitDisabled) return;

    createMutation.mutate(
      { placeId, rating, content, localPhotoUris: photoUris, petPolicyAccurate },
      {
        onSuccess: () => {
          setErrorMessage(undefined);
          setCompleteModalVisible(true);
        },
        onError: () => setErrorMessage('리뷰를 등록하지 못했어요. 잠시 후 다시 시도해 주세요.'),
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
      <ScreenHeader title="리뷰 작성" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <LabeledField label="별점">
            <StarRating onChange={setRating} rating={rating} size={32} />
          </LabeledField>

          <LabeledField label="리뷰 내용">
            <View style={styles.textAreaBox}>
              <TextInput
                editable={!isSaving}
                maxLength={REVIEW_CONTENT_MAX_LENGTH}
                multiline
                onChangeText={setContent}
                placeholder="반려동물과 함께한 경험을 남겨주세요."
                placeholderTextColor={colors.textSecondary}
                style={styles.textArea}
                textAlignVertical="top"
                value={content}
              />
              <Text style={styles.counter}>
                {content.length}/{REVIEW_CONTENT_MAX_LENGTH}
              </Text>
            </View>
          </LabeledField>

          <LabeledField label="사진 첨부">
            <PhotoPicker
              disabled={isSaving}
              imageUris={photoUris}
              maxImages={REVIEW_PHOTO_MAX_COUNT}
              onAdd={() => void addPhotos()}
              onRemove={removePhoto}
            />
          </LabeledField>

          <LabeledField label="동반정책 정보가 실제와 맞았나요?">
            <View style={styles.choiceRow}>
              <Pressable
                onPress={() => setPetPolicyAccurate(true)}
                style={[styles.choiceChip, petPolicyAccurate === true && styles.choiceChipSelected]}
              >
                <Text
                  style={[
                    styles.choiceChipText,
                    petPolicyAccurate === true && styles.choiceChipTextSelected,
                  ]}
                >
                  정확했어요
                </Text>
              </Pressable>
              <Pressable
                onPress={() => setPetPolicyAccurate(false)}
                style={[styles.choiceChip, petPolicyAccurate === false && styles.choiceChipSelected]}
              >
                <Text
                  style={[
                    styles.choiceChipText,
                    petPolicyAccurate === false && styles.choiceChipTextSelected,
                  ]}
                >
                  달랐어요
                </Text>
              </Pressable>
            </View>
          </LabeledField>

          {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}
        </ScrollView>

        <View style={styles.footer}>
          <Button
            disabled={isSubmitDisabled}
            label={isSaving ? '등록 중...' : '리뷰 등록'}
            onPress={handleSubmit}
            size="md"
            variant="primary"
          />
        </View>
      </KeyboardAvoidingView>

      <DiscardChangesModal
        description="작성한 리뷰 내용이 저장되지 않아요."
        onContinue={continueEditing}
        onDiscard={discardChanges}
        visible={discardModalVisible}
      />
      <SaveCompleteModal
        description="다른 여행자들에게 도움이 될 거예요."
        onConfirm={closeComplete}
        title="리뷰가 등록되었어요"
        visible={completeModalVisible}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  choiceChip: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.full,
    borderWidth: 1,
    flex: 1,
    paddingVertical: spacing.sm + 2,
  },
  choiceChipSelected: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  choiceChipText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  choiceChipTextSelected: {
    color: colors.primary,
  },
  choiceRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
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
  mutationError: {
    color: colors.error,
    fontSize: 13,
    textAlign: 'center',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  textArea: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    lineHeight: 22,
    minHeight: 100,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  textAreaBox: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
  },
});

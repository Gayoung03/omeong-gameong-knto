import { useNavigation } from 'expo-router';
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

import { Button } from '@/src/components/ui/Button';
import { LabeledField } from '@/src/components/ui/LabeledField';
import { PhotoPicker } from '@/src/components/ui/PhotoPicker';
import { DiscardChangesModal } from '@/src/features/profile/components/DiscardChangesModal';
import { SaveCompleteModal } from '@/src/features/profile/components/SaveCompleteModal';
import { colors, radius, spacing, typography } from '@/src/theme';

import { StarRating } from './StarRating';
import { REVIEW_CONTENT_MAX_LENGTH, REVIEW_PHOTO_MAX_COUNT } from '../types/review';

export type ReviewFormValues = {
  rating: number;
  content: string;
  /** 새로 고른 로컬 URI 와 이미 올라간 서버 URL 이 섞여 있다. 업로드 단계가 구분한다. */
  photoUris: string[];
  petPolicyAccurate: boolean | null;
};

const EMPTY_VALUES: ReviewFormValues = {
  content: '',
  petPolicyAccurate: null,
  photoUris: [],
  rating: 0,
};

type ReviewFormProps = {
  /** 수정 화면은 기존 값으로 시작한다. 값이 바뀌어도 다시 읽지 않는 초기값이다. */
  initialValues?: ReviewFormValues;
  submitLabel: string;
  savingLabel: string;
  isSaving: boolean;
  errorMessage?: string;
  /** 저장이 끝나 완료 모달을 띄울지. 화면(부모)이 결정한다. */
  isComplete: boolean;
  completeTitle: string;
  completeDescription: string;
  discardDescription: string;
  onSubmit: (values: ReviewFormValues) => void;
  onCompleteConfirm: () => void;
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

/**
 * 리뷰 작성·수정이 공유하는 입력 폼.
 *
 * 두 화면의 입력 항목이 같아서 하나로 뒀다. 다른 것은 초기값과 버튼 문구뿐이고,
 * 서버 호출은 각 화면이 자기 훅으로 한다.
 */
export function ReviewForm({
  initialValues = EMPTY_VALUES,
  submitLabel,
  savingLabel,
  isSaving,
  errorMessage,
  isComplete,
  completeTitle,
  completeDescription,
  discardDescription,
  onSubmit,
  onCompleteConfirm,
}: ReviewFormProps) {
  const navigation = useNavigation();

  const [rating, setRating] = useState(initialValues.rating);
  const [content, setContent] = useState(initialValues.content);
  const [photoUris, setPhotoUris] = useState<string[]>(initialValues.photoUris);
  const [petPolicyAccurate, setPetPolicyAccurate] = useState<boolean | null>(
    initialValues.petPolicyAccurate,
  );
  const [photoErrorMessage, setPhotoErrorMessage] = useState<string>();
  const [discardModalVisible, setDiscardModalVisible] = useState(false);

  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);

  const isDirty =
    rating !== initialValues.rating ||
    content !== initialValues.content ||
    petPolicyAccurate !== initialValues.petPolicyAccurate ||
    photoUris.join('|') !== initialValues.photoUris.join('|');

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
        setPhotoErrorMessage(undefined);
      }
    } catch {
      setPhotoErrorMessage('사진 앨범을 열 수 없어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  const removePhoto = (uri: string) => {
    setPhotoUris((current) => current.filter((item) => item !== uri));
  };

  const handleSubmit = () => {
    Keyboard.dismiss();
    if (isSubmitDisabled) return;

    onSubmit({ content, petPolicyAccurate, photoUris, rating });
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
    // 저장이 끝났으니 "나가면 사라져요" 안내가 뜨면 안 된다.
    allowExitRef.current = true;
    onCompleteConfirm();
  };

  return (
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

        {photoErrorMessage && <Text style={styles.mutationError}>{photoErrorMessage}</Text>}
        {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}
      </ScrollView>

      <View style={styles.footer}>
        <Button
          disabled={isSubmitDisabled}
          label={isSaving ? savingLabel : submitLabel}
          onPress={handleSubmit}
          size="md"
          variant="primary"
        />
      </View>

      <DiscardChangesModal
        description={discardDescription}
        onContinue={continueEditing}
        onDiscard={discardChanges}
        visible={discardModalVisible}
      />
      <SaveCompleteModal
        description={completeDescription}
        onConfirm={closeComplete}
        title={completeTitle}
        visible={isComplete}
      />
    </KeyboardAvoidingView>
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
    fontSize: typography.caption.fontSize,
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
    fontSize: typography.label.fontSize,
    textAlign: 'center',
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

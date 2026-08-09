import Ionicons from '@expo/vector-icons/Ionicons';
import * as ImagePicker from 'expo-image-picker';
import { useNavigation, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Alert, Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { usePets } from '@/src/features/profile/hooks/usePets';
import { colors, radius, shadow, spacing, typography } from '@/src/theme';

import { LogCreationCancelModal } from './components/LogCreationCancelModal';
import { MomentStepHeader } from './components/MomentStepHeader';
import {
  PhotoChangeBottomSheet,
  type PhotoChangeBottomSheetHandle,
} from './components/PhotoChangeBottomSheet';
import { useLogDraftStore } from './stores/useLogDraftStore';

const MAX_PHOTO_BYTES = 15 * 1024 * 1024;

function showPermissionAlert(kind: '카메라' | '사진 앨범') {
  Alert.alert(
    `${kind} 권한이 필요해요`,
    `사진을 선택하려면 설정에서 ${kind} 접근을 허용해 주세요.`,
    [
      { text: '취소', style: 'cancel' },
      { text: '설정 열기', onPress: () => Linking.openSettings() },
    ],
  );
}

export function NewMomentPhotoStepScreen() {
  const router = useRouter();
  const navigation = useNavigation();
  const draft = useLogDraftStore((state) => state.draft);
  const updateDraft = useLogDraftStore((state) => state.updateDraft);
  const resetDraft = useLogDraftStore((state) => state.resetDraft);
  // 기본 선택값도 활성 프로필에서만 고른다.
  const { data: pets = [] } = usePets();
  const photoChangeSheetRef = useRef<PhotoChangeBottomSheetHandle>(null);
  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);
  const [cancelModalVisible, setCancelModalVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();
  const hasDraftContent = Boolean(
    draft.localPhotoUri ||
      draft.tripId ||
      draft.recordedDate ||
      draft.placeId ||
      draft.placeName ||
      draft.petIds.length > 0 ||
      draft.writingStyle !== 'dog_diary' ||
      draft.mood ||
      draft.personalMessage.trim(),
  );

  useEffect(() => {
    return navigation.addListener('beforeRemove', (event) => {
      if (allowExitRef.current || !hasDraftContent) return;

      event.preventDefault();
      if (exitModalOpenRef.current) return;
      exitModalOpenRef.current = true;
      pendingExitRef.current = () => navigation.dispatch(event.data.action);
      setCancelModalVisible(true);
    });
  }, [hasDraftContent, navigation]);

  const requestExit = () => {
    if (!hasDraftContent) {
      allowExitRef.current = true;
      router.replace('/travel-logs');
      return;
    }
    if (exitModalOpenRef.current) return;
    exitModalOpenRef.current = true;
    pendingExitRef.current = () => router.replace('/travel-logs');
    setCancelModalVisible(true);
  };

  const continueWriting = () => {
    exitModalOpenRef.current = false;
    pendingExitRef.current = null;
    setCancelModalVisible(false);
  };

  const cancelCreation = () => {
    const exit = pendingExitRef.current;
    allowExitRef.current = true;
    exitModalOpenRef.current = false;
    pendingExitRef.current = null;
    setCancelModalVisible(false);
    resetDraft();
    exit?.();
  };

  const saveAsset = (asset: ImagePicker.ImagePickerAsset) => {
    if (asset.fileSize && asset.fileSize > MAX_PHOTO_BYTES) {
      setErrorMessage('사진 용량이 너무 커요. 15MB 이하의 사진을 선택해 주세요.');
      return;
    }
    setErrorMessage(undefined);
    updateDraft({
      localPhotoUri: asset.uri,
      photoFileName: asset.fileName ?? undefined,
      photoMimeType: asset.mimeType ?? undefined,
      photoFileSize: asset.fileSize,
      photoWidth: asset.width,
      photoHeight: asset.height,
      petIds: draft.petIds.length > 0 ? draft.petIds : pets[0] ? [pets[0].petId] : [],
    });
  };

  const takePhoto = async () => {
    try {
      const permission = await ImagePicker.requestCameraPermissionsAsync();
      if (!permission.granted) {
        showPermissionAlert('카메라');
        return;
      }
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: false,
        mediaTypes: ['images'],
        quality: 0.9,
      });
      if (!result.canceled && result.assets[0]) saveAsset(result.assets[0]);
    } catch {
      setErrorMessage('카메라를 열 수 없어요. 이 기기에서 카메라를 사용할 수 있는지 확인해 주세요.');
    }
  };

  const selectFromAlbum = async () => {
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        showPermissionAlert('사진 앨범');
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        allowsMultipleSelection: false,
        mediaTypes: ['images'],
        quality: 0.9,
        selectionLimit: 1,
      });
      if (!result.canceled && result.assets[0]) saveAsset(result.assets[0]);
    } catch {
      setErrorMessage('사진 앨범을 열 수 없어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  const clearPhoto = () => {
    setErrorMessage(undefined);
    const hasLaterStepContent = Boolean(
      draft.tripId ||
        draft.recordedDate ||
        draft.placeId ||
        draft.placeName ||
        draft.writingStyle !== 'dog_diary' ||
        draft.mood ||
        draft.personalMessage.trim(),
    );
    updateDraft({
      localPhotoUri: null,
      photoFileName: undefined,
      photoMimeType: undefined,
      photoFileSize: undefined,
      photoWidth: undefined,
      photoHeight: undefined,
      petIds: hasLaterStepContent ? draft.petIds : [],
    });
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <MomentStepHeader onBack={requestExit} step={1} title="간직하고 싶은 순간을 골라주세요" />
      <View style={styles.content}>
        {draft.localPhotoUri ? (
          <View style={styles.selectedArea}>
            <View style={styles.photoFrame}>
              <RemoteImage borderRadius={radius.lg} style={styles.preview} uri={draft.localPhotoUri} />
              <Pressable
                accessibilityLabel="사진 변경 메뉴 열기"
                accessibilityRole="button"
                onPress={() => photoChangeSheetRef.current?.open()}
                style={[styles.changeButton, shadow.sm]}
              >
                <Ionicons color={colors.textPrimary} name="image-outline" size={19} />
                <Text style={styles.changeButtonLabel}>사진 변경</Text>
              </Pressable>
            </View>
            <View style={styles.helperRow}>
              <Ionicons color={colors.iconGray} name="information-circle-outline" size={16} />
              <Text style={styles.helper}>사진 한 장을 선택할 수 있어요</Text>
            </View>
          </View>
        ) : (
          <View style={styles.emptyState}>
            <View style={styles.emptyPreview}>
              <Ionicons color={colors.iconGray} name="image-outline" size={54} />
              <Text style={styles.emptyTitle}>여행 사진을 선택해 주세요</Text>
            </View>
            <View style={styles.sourceActions}>
              <Pressable onPress={takePhoto} style={styles.sourceButton}>
                <Ionicons color={colors.secondary} name="camera-outline" size={24} />
                <Text style={styles.sourceLabel}>카메라로 촬영</Text>
              </Pressable>
              <Pressable onPress={selectFromAlbum} style={styles.sourceButton}>
                <Ionicons color={colors.secondary} name="images-outline" size={24} />
                <Text style={styles.sourceLabel}>앨범에서 선택</Text>
              </Pressable>
            </View>
            <View style={styles.helperRow}>
              <Ionicons color={colors.iconGray} name="information-circle-outline" size={16} />
              <Text style={styles.helper}>사진 한 장을 선택할 수 있어요</Text>
            </View>
          </View>
        )}
        {errorMessage ? <Text style={styles.error}>{errorMessage}</Text> : null}
      </View>
      <View style={styles.footer}>
        <Pressable
          accessibilityState={{ disabled: !draft.localPhotoUri }}
          disabled={!draft.localPhotoUri}
          onPress={() => router.push('/travel-logs/new-moment/details')}
          style={[styles.nextButton, !draft.localPhotoUri && styles.nextButtonDisabled]}
        >
          <Text style={[styles.nextLabel, !draft.localPhotoUri && styles.nextLabelDisabled]}>다음</Text>
        </Pressable>
      </View>
      <PhotoChangeBottomSheet
        onDelete={clearPhoto}
        onSelectAlbum={selectFromAlbum}
        onTakePhoto={takePhoto}
        ref={photoChangeSheetRef}
      />
      <LogCreationCancelModal
        onCancelCreation={cancelCreation}
        onContinue={continueWriting}
        visible={cancelModalVisible}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  changeButton: {
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.94)',
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    bottom: spacing.md,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: spacing.md,
    position: 'absolute',
    right: spacing.md,
  },
  changeButtonLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
  content: { alignSelf: 'center', flex: 1, gap: spacing.md, maxWidth: 680, paddingHorizontal: spacing.md, width: '100%' },
  emptyState: { flex: 1, gap: spacing.md },
  emptyPreview: { alignItems: 'center', backgroundColor: colors.neutralGray, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, flex: 1, justifyContent: 'center', maxHeight: 430, minHeight: 280 },
  emptyTitle: { color: colors.textSecondary, fontSize: typography.body.fontSize, marginTop: spacing.sm },
  error: { color: colors.error, fontSize: 13, textAlign: 'center' },
  footer: { padding: spacing.md },
  helper: { color: colors.textSecondary, fontSize: 12 },
  helperRow: { alignItems: 'center', flexDirection: 'row', gap: spacing.xs, justifyContent: 'center' },
  nextButton: { alignItems: 'center', backgroundColor: colors.primary, borderRadius: radius.sm, paddingVertical: 14 },
  nextButtonDisabled: { backgroundColor: colors.neutralGray },
  nextLabel: { color: colors.surface, fontSize: typography.body.fontSize, fontWeight: '700' },
  nextLabelDisabled: { color: colors.textSecondary },
  photoFrame: { borderRadius: radius.lg, flex: 1, minHeight: 250, overflow: 'hidden', position: 'relative', width: '100%' },
  preview: { height: '100%', width: '100%' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  selectedArea: { flex: 1, gap: spacing.md, minHeight: 0 },
  sourceActions: { flexDirection: 'row', gap: spacing.sm },
  sourceButton: { alignItems: 'center', backgroundColor: colors.mintBg, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, flex: 1, gap: spacing.xs, justifyContent: 'center', minHeight: 78, padding: spacing.sm },
  sourceLabel: { color: colors.secondary, fontSize: 13, fontWeight: '600' },
});

import * as ImagePicker from 'expo-image-picker';
import { useNavigation } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Alert, Keyboard, KeyboardAvoidingView, Linking, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/src/components/ui/Button';
import { colors, radius, spacing, typography } from '@/src/theme';

import { DiscardChangesModal } from './components/DiscardChangesModal';
import { ProfileEditHeader } from './components/ProfileEditHeader';
import { ProfileImageChangeBottomSheet, type ProfileImageChangeBottomSheetHandle } from './components/ProfileImageChangeBottomSheet';
import { ProfileImagePicker } from './components/ProfileImagePicker';
import { SaveCompleteModal } from './components/SaveCompleteModal';
import { useUpdateUserProfile } from './hooks/useUpdateUserProfile';
import { useUserProfile } from './hooks/useUserProfile';
import { validateNickname } from './utils/validateNickname';

function showPermissionAlert() {
  Alert.alert(
    '사진 앨범 권한이 필요해요',
    '프로필 이미지를 선택하려면 설정에서 사진 앨범 접근을 허용해 주세요.',
    [
      { text: '취소', style: 'cancel' },
      { text: '설정 열기', onPress: () => Linking.openSettings() },
    ],
  );
}

export function ProfileEditScreen() {
  const navigation = useNavigation();
  const { data: user } = useUserProfile();
  const { mutate, isPending: isSaving } = useUpdateUserProfile();

  const [nickname, setNickname] = useState('');
  const [localImageUri, setLocalImageUri] = useState<string | undefined>();
  const [imageReset, setImageReset] = useState(false);
  const [discardModalVisible, setDiscardModalVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();
  const [saveCompleteVisible, setSaveCompleteVisible] = useState(false);

  const imageChangeSheetRef = useRef<ProfileImageChangeBottomSheetHandle>(null);
  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);
  const userIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (user && user.userId !== userIdRef.current) {
      userIdRef.current = user.userId;
      setNickname(user.nickname);
    }
  }, [user]);

  const nicknameError = validateNickname(nickname);
  const displayImageUri = localImageUri ?? (imageReset ? undefined : user?.profileImage);
  const nicknameChanged = user ? nickname.trim() !== user.nickname : false;
  const imageChanged = localImageUri !== undefined || imageReset;
  const isDirty = nicknameChanged || imageChanged;
  const isSaveDisabled = !isDirty || nicknameError !== null || isSaving;

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

  const selectFromAlbum = async () => {
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        showPermissionAlert();
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        allowsMultipleSelection: false,
        mediaTypes: ['images'],
        quality: 0.9,
        selectionLimit: 1,
      });
      if (!result.canceled && result.assets[0]) {
        setLocalImageUri(result.assets[0].uri);
        setImageReset(false);
        setErrorMessage(undefined);
      }
    } catch {
      setErrorMessage('사진 앨범을 열 수 없어요. 잠시 후 다시 시도해 주세요.');
    }
  };

  const resetToDefault = () => {
    setLocalImageUri(undefined);
    setImageReset(true);
    setErrorMessage(undefined);
  };

  const handleSave = () => {
    Keyboard.dismiss();
    if (isSaveDisabled) return;

    mutate(
      {
        nickname: nickname.trim(),
        localProfileImageUri: localImageUri,
        resetProfileImage: imageReset,
      },
      {
        onSuccess: (updatedUser) => {
          setNickname(updatedUser.nickname);
          setLocalImageUri(undefined);
          setImageReset(false);
          setErrorMessage(undefined);
          setSaveCompleteVisible(true);
        },
        onError: () => {
          setErrorMessage('프로필을 저장할 수 없었어요. 잠시 후 다시 시도해 주세요.');
        },
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

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ProfileEditHeader />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <ProfileImagePicker imageUri={displayImageUri} onPress={() => imageChangeSheetRef.current?.open()} />

          <View style={styles.section}>
            <Text style={styles.label}>닉네임</Text>
            <TextInput
              editable={!isSaving}
              maxLength={12}
              onChangeText={(text) => {
                setNickname(text.replace(/\n/g, ''));
              }}
              placeholder="닉네임을 입력해 주세요"
              placeholderTextColor={colors.textSecondary}
              style={[styles.input, nicknameError && styles.inputError]}
              value={nickname}
            />
            {nicknameError && <Text style={styles.errorText}>{nicknameError}</Text>}
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>이메일</Text>
            <View style={styles.readOnlyInputContainer}>
              <Text style={styles.readOnlyText}>{user?.email}</Text>
            </View>
            <Text style={styles.helperText}>이메일은 변경할 수 없습니다</Text>
          </View>

          {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}
        </ScrollView>

        <View style={styles.footer}>
          <Button
            disabled={isSaveDisabled}
            label={isSaving ? '저장 중...' : '변경사항 저장'}
            onPress={handleSave}
            size="md"
            variant="primary"
          />
        </View>
      </KeyboardAvoidingView>

      <ProfileImageChangeBottomSheet onResetToDefault={resetToDefault} onSelectAlbum={selectFromAlbum} ref={imageChangeSheetRef} />
      <DiscardChangesModal onContinue={continueEditing} onDiscard={discardChanges} visible={discardModalVisible} />
      <SaveCompleteModal onConfirm={() => setSaveCompleteVisible(false)} visible={saveCompleteVisible} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  errorText: {
    color: colors.error,
    fontSize: 12,
    marginTop: spacing.xs,
  },
  flex: {
    flex: 1,
  },
  footer: {
    backgroundColor: colors.background,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  helperText: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: spacing.xs,
  },
  input: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  inputError: {
    borderColor: colors.error,
  },
  label: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '600',
  },
  mutationError: {
    color: colors.error,
    fontSize: 13,
    marginHorizontal: spacing.lg,
    textAlign: 'center',
  },
  readOnlyInputContainer: {
    backgroundColor: colors.neutralGray,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  readOnlyText: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  section: {
    gap: spacing.xs,
  },
});

import * as ImagePicker from 'expo-image-picker';
import { useNavigation, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
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
import { Chip, ChipRow } from '@/src/components/ui/Chip';
import { colors, radius, spacing, typography } from '@/src/theme';
import {
  OTHER_SPECIES,
  PET_SIZE_OPTIONS,
  PET_SPECIES_OPTIONS,
  suggestPetSize,
  type Pet,
  type PetSize,
  type PetSpecies,
} from '@/src/types/pet';

import { DiscardChangesModal } from './components/DiscardChangesModal';
import { PetDeleteConfirmModal } from './components/PetDeleteConfirmModal';
import { PetFormHeader } from './components/PetFormHeader';
import { ProfileImageChangeBottomSheet, type ProfileImageChangeBottomSheetHandle } from './components/ProfileImageChangeBottomSheet';
import { ProfileImagePicker } from './components/ProfileImagePicker';
import { SaveCompleteModal } from './components/SaveCompleteModal';
import { useCreatePet } from './hooks/useCreatePet';
import { useDeletePet } from './hooks/useDeletePet';
import { usePets } from './hooks/usePets';
import { useUpdatePet } from './hooks/useUpdatePet';
import { hasPetFormError, validatePetForm } from './utils/validatePetForm';

type Props = {
  /** 없으면 등록, 있으면 수정 모드 */
  petId?: string;
};

function showPermissionAlert() {
  Alert.alert(
    '사진 앨범 권한이 필요해요',
    '반려동물 사진을 선택하려면 설정에서 사진 앨범 접근을 허용해 주세요.',
    [
      { text: '취소', style: 'cancel' },
      { text: '설정 열기', onPress: () => Linking.openSettings() },
    ],
  );
}

export function PetFormScreen({ petId }: Props) {
  const router = useRouter();
  const navigation = useNavigation();
  const isEditMode = petId !== undefined;

  // 캐시에 목록이 없으면 usePets가 fetchPets를 실행하고, 그 결과에서 petId로 다시 찾는다.
  // 이름으로는 절대 찾지 않는다.
  const { data: pets, isPending: isLoadingPets } = usePets();
  const editingPet: Pet | undefined = useMemo(
    () => (isEditMode ? pets?.find((pet) => pet.petId === petId) : undefined),
    [isEditMode, petId, pets],
  );
  const isMissingPet = isEditMode && !isLoadingPets && !editingPet;

  const createMutation = useCreatePet();
  const updateMutation = useUpdatePet();
  const deleteMutation = useDeletePet();
  const isSaving = createMutation.isPending || updateMutation.isPending;

  const [name, setName] = useState('');
  const [species, setSpecies] = useState<PetSpecies>(PET_SPECIES_OPTIONS[0]);
  const [speciesDetail, setSpeciesDetail] = useState('');
  const [breed, setBreed] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [weight, setWeight] = useState('');
  const [size, setSize] = useState<PetSize>(PET_SIZE_OPTIONS[0]);
  /** 사용자가 크기를 직접 고른 뒤에는 몸무게가 바뀌어도 자동 추천이 덮어쓰지 않는다. */
  const [isSizeChosen, setIsSizeChosen] = useState(false);
  const [localImageUri, setLocalImageUri] = useState<string | undefined>();
  const [imageReset, setImageReset] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();
  const [discardModalVisible, setDiscardModalVisible] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [saveCompleteVisible, setSaveCompleteVisible] = useState(false);

  const imageChangeSheetRef = useRef<ProfileImageChangeBottomSheetHandle>(null);
  const allowExitRef = useRef(false);
  const exitModalOpenRef = useRef(false);
  const pendingExitRef = useRef<(() => void) | null>(null);
  const loadedPetIdRef = useRef<string | undefined>(undefined);

  // 수정 대상 데이터가 도착하면 폼을 한 번만 채운다.
  useEffect(() => {
    if (editingPet && editingPet.petId !== loadedPetIdRef.current) {
      loadedPetIdRef.current = editingPet.petId;
      setName(editingPet.name);
      setSpecies(editingPet.species);
      setSpeciesDetail(editingPet.speciesDetail ?? '');
      setBreed(editingPet.breed ?? '');
      setBirthDate(editingPet.birthDate ?? '');
      setWeight(editingPet.weight === null ? '' : String(editingPet.weight));
      setSize(editingPet.size ?? PET_SIZE_OPTIONS[0]);
      // 저장된 값이 있으니 자동 추천이 끼어들지 않게 한다.
      setIsSizeChosen(editingPet.size !== null);
    }
  }, [editingPet]);

  // 지워졌거나 존재하지 않는 프로필이면 안내 후 마이페이지로 돌려보낸다.
  useEffect(() => {
    if (!isMissingPet) return;

    allowExitRef.current = true;
    Alert.alert('프로필을 찾을 수 없어요', '이미 지웠거나 존재하지 않는 반려동물이에요.', [
      { text: '확인', onPress: () => router.back() },
    ]);
  }, [isMissingPet, router]);

  const isOtherSpecies = species === OTHER_SPECIES;

  const handleChangeWeight = (text: string) => {
    setWeight(text);
    if (isSizeChosen) return;

    const suggested = suggestPetSize(Number(text.trim()));
    if (suggested) setSize(suggested);
  };

  const handleChangeSize = (next: PetSize) => {
    setSize(next);
    setIsSizeChosen(true);
  };

  const handleChangeSpecies = (next: PetSpecies) => {
    setSpecies(next);
    if (next !== OTHER_SPECIES) setSpeciesDetail('');
  };

  const errors = validatePetForm({
    name,
    speciesDetail: isOtherSpecies ? speciesDetail : undefined,
    breed,
    birthDate,
    weight,
  });
  const displayImageUri = localImageUri ?? (imageReset ? undefined : editingPet?.profileImage);

  const isDirty = isEditMode
    ? Boolean(
        editingPet &&
          (name.trim() !== editingPet.name ||
            species !== editingPet.species ||
            speciesDetail.trim() !== (editingPet.speciesDetail ?? '') ||
            size !== (editingPet.size ?? PET_SIZE_OPTIONS[0]) ||
            breed.trim() !== (editingPet.breed ?? '') ||
            birthDate.trim() !== (editingPet.birthDate ?? '') ||
            weight.trim() !== (editingPet.weight === null ? '' : String(editingPet.weight)) ||
            localImageUri !== undefined ||
            imageReset),
      )
    : Boolean(name || speciesDetail || breed || birthDate || weight || localImageUri);

  const isSaveDisabled = !isDirty || hasPetFormError(errors) || isSaving;

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
        // 새 이미지를 고르면 '기본 이미지로 변경' 의도는 취소된다. 두 상태는 동시에 켜지지 않는다.
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

    const input = {
      name,
      species,
      speciesDetail: isOtherSpecies ? speciesDetail.trim() : undefined,
      breed,
      birthDate: birthDate.trim(),
      weight: Number(weight.trim()),
      size,
      localProfileImageUri: localImageUri,
      removeProfileImage: imageReset,
    };

    // 이미지 업로드가 실패하면 mutation 전체가 실패해 저장이 완료 처리되지 않는다.
    const onError = (error: unknown) =>
      setErrorMessage(
        error instanceof Error ? error.message : '저장하지 못했어요. 잠시 후 다시 시도해 주세요.',
      );

    if (isEditMode && petId) {
      updateMutation.mutate(
        { petId, input },
        {
          onSuccess: () => {
            setLocalImageUri(undefined);
            setImageReset(false);
            setErrorMessage(undefined);
            setSaveCompleteVisible(true);
          },
          onError,
        },
      );
      return;
    }

    createMutation.mutate(input, {
      onSuccess: () => {
        setErrorMessage(undefined);
        setSaveCompleteVisible(true);
      },
      onError,
    });
  };

  const confirmDelete = () => {
    if (!petId || deleteMutation.isPending) return;

    deleteMutation.mutate(petId, {
      onSuccess: () => {
        setDeleteModalVisible(false);
        allowExitRef.current = true;
        router.back();
      },
      onError: () => {
        // 실패해도 화면을 유지해 그대로 다시 시도할 수 있게 한다.
        setDeleteModalVisible(false);
        setErrorMessage('프로필을 지우지 못했어요. 잠시 후 다시 시도해 주세요.');
      },
    });
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

  const closeSaveComplete = () => {
    setSaveCompleteVisible(false);
    allowExitRef.current = true;
    router.back();
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <PetFormHeader title={isEditMode ? '반려동물 수정' : '반려동물 등록'} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <ProfileImagePicker imageUri={displayImageUri} onPress={() => imageChangeSheetRef.current?.open()} />

          <View style={styles.section}>
            <Text style={styles.label}>이름</Text>
            <TextInput
              editable={!isSaving}
              maxLength={10}
              onChangeText={(text) => setName(text.replace(/\n/g, ''))}
              placeholder="이름을 입력해 주세요"
              placeholderTextColor={colors.textSecondary}
              style={[styles.input, errors.name && styles.inputError]}
              value={name}
            />
            {errors.name && <Text style={styles.errorText}>{errors.name}</Text>}
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>종</Text>
            <ChipRow>
              {PET_SPECIES_OPTIONS.map((option) => (
                <Chip
                  key={option}
                  label={option}
                  onPress={() => handleChangeSpecies(option)}
                  selected={species === option}
                />
              ))}
            </ChipRow>
            {isOtherSpecies && (
              <>
                <TextInput
                  editable={!isSaving}
                  maxLength={20}
                  onChangeText={(text) => setSpeciesDetail(text.replace(/\n/g, ''))}
                  placeholder="종 이름을 입력해 주세요"
                  placeholderTextColor={colors.textSecondary}
                  style={[
                    styles.input,
                    styles.speciesDetailInput,
                    errors.speciesDetail && styles.inputError,
                  ]}
                  value={speciesDetail}
                />
                {errors.speciesDetail && (
                  <Text style={styles.errorText}>{errors.speciesDetail}</Text>
                )}
              </>
            )}
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>품종</Text>
            <TextInput
              editable={!isSaving}
              maxLength={20}
              onChangeText={(text) => setBreed(text.replace(/\n/g, ''))}
              placeholder="품종을 입력해 주세요"
              placeholderTextColor={colors.textSecondary}
              style={[styles.input, errors.breed && styles.inputError]}
              value={breed}
            />
            {errors.breed && <Text style={styles.errorText}>{errors.breed}</Text>}
          </View>

          <View style={styles.row}>
            <View style={[styles.section, styles.flex]}>
              <Text style={styles.label}>생년월일</Text>
              <TextInput
                editable={!isSaving}
                maxLength={10}
                onChangeText={setBirthDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.textSecondary}
                style={[styles.input, errors.birthDate && styles.inputError]}
                value={birthDate}
              />
              {errors.birthDate && <Text style={styles.errorText}>{errors.birthDate}</Text>}
            </View>

            <View style={[styles.section, styles.flex]}>
              <Text style={styles.label}>몸무게(kg)</Text>
              <TextInput
                editable={!isSaving}
                keyboardType="decimal-pad"
                maxLength={5}
                onChangeText={handleChangeWeight}
                placeholder="0.0"
                placeholderTextColor={colors.textSecondary}
                style={[styles.input, errors.weight && styles.inputError]}
                value={weight}
              />
              {errors.weight && <Text style={styles.errorText}>{errors.weight}</Text>}
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.label}>크기</Text>
            <ChipRow>
              {PET_SIZE_OPTIONS.map((option) => (
                <Chip
                  key={option}
                  label={option}
                  onPress={() => handleChangeSize(option)}
                  selected={size === option}
                />
              ))}
            </ChipRow>
            <Text style={styles.sizeHint}>몸무게를 입력하면 자동으로 골라드려요. 직접 바꿔도 됩니다.</Text>
          </View>

          {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}

          {isEditMode && editingPet && (
            <Pressable
              accessibilityRole="button"
              onPress={() => setDeleteModalVisible(true)}
              style={styles.deleteButton}
            >
              <Text style={styles.deleteLabel}>이 프로필 지우기</Text>
            </Pressable>
          )}
        </ScrollView>

        <View style={styles.footer}>
          <Button
            disabled={isSaveDisabled}
            label={isSaving ? '저장 중...' : isEditMode ? '변경사항 저장' : '등록하기'}
            onPress={handleSave}
            size="md"
            variant="primary"
          />
        </View>
      </KeyboardAvoidingView>

      <ProfileImageChangeBottomSheet
        onResetToDefault={resetToDefault}
        onSelectAlbum={selectFromAlbum}
        ref={imageChangeSheetRef}
        title="반려동물 사진 변경"
      />
      <DiscardChangesModal
        description="입력한 반려동물 정보가 저장되지 않아요."
        onContinue={continueEditing}
        onDiscard={discardChanges}
        visible={discardModalVisible}
      />
      <PetDeleteConfirmModal
        isDeleting={deleteMutation.isPending}
        onCancel={() => setDeleteModalVisible(false)}
        onConfirm={confirmDelete}
        petName={editingPet?.name ?? ''}
        visible={deleteModalVisible}
      />
      <SaveCompleteModal
        description={isEditMode ? '반려동물 정보가 업데이트되었어요.' : '반려동물이 등록되었어요.'}
        onConfirm={closeSaveComplete}
        title={isEditMode ? '변경사항이 저장되었어요' : '등록이 완료되었어요'}
        visible={saveCompleteVisible}
      />
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
  deleteButton: {
    alignItems: 'center',
    paddingVertical: spacing.md,
  },
  deleteLabel: {
    color: colors.error,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
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
  speciesDetailInput: {
    marginTop: spacing.sm,
  },
  sizeHint: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
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
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  section: {
    gap: spacing.xs,
  },
});

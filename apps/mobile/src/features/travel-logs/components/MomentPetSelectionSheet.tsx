import Ionicons from '@expo/vector-icons/Ionicons';
import {
  BottomSheetBackdrop,
  BottomSheetModal,
  BottomSheetView,
  type BottomSheetBackdropProps,
} from '@gorhom/bottom-sheet';
import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { Pet } from '@/src/types/pet';

export type MomentPetSelectionSheetHandle = { open: () => void };

type Props = {
  pets: Pet[];
  value: string[];
  onApply: (petIds: string[]) => void;
};

export const MomentPetSelectionSheet = forwardRef<MomentPetSelectionSheetHandle, Props>(
  function MomentPetSelectionSheet({ pets, value, onApply }, ref) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const [pendingIds, setPendingIds] = useState(value);

    useImperativeHandle(
      ref,
      () => ({
        open: () => {
          setPendingIds(value);
          sheetRef.current?.present();
        },
      }),
      [value],
    );

    const dismiss = useCallback(() => sheetRef.current?.dismiss(), []);
    const apply = useCallback(() => {
      onApply(pendingIds);
      dismiss();
    }, [dismiss, onApply, pendingIds]);
    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />
      ),
      [],
    );

    return (
      <BottomSheetModal backdropComponent={renderBackdrop} enablePanDownToClose ref={sheetRef}>
        <BottomSheetView style={styles.sheet}>
          <Text style={styles.title}>함께한 반려동물</Text>
          <View style={styles.list}>
            {pets.map((pet) => {
              const selected = pendingIds.includes(pet.petId);
              return (
                <Pressable
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  key={pet.petId}
                  onPress={() =>
                    setPendingIds((current) =>
                      current.includes(pet.petId)
                        ? current.filter((id) => id !== pet.petId)
                        : [...current, pet.petId],
                    )
                  }
                  style={styles.petRow}
                >
                  <Avatar fallbackIcon="paw" size={38} uri={pet.profileImage} />
                  <Text style={styles.petName}>{pet.name}</Text>
                  <Ionicons
                    color={selected ? colors.primary : colors.iconGray}
                    name={selected ? 'checkmark-circle' : 'ellipse-outline'}
                    size={24}
                  />
                </Pressable>
              );
            })}
          </View>
          <View style={styles.footer}>
            <Pressable onPress={dismiss} style={[styles.button, styles.cancelButton]}>
              <Text style={styles.cancelLabel}>취소</Text>
            </Pressable>
            <Pressable onPress={apply} style={[styles.button, styles.applyButton]}>
              <Text style={styles.applyLabel}>선택 완료</Text>
            </Pressable>
          </View>
        </BottomSheetView>
      </BottomSheetModal>
    );
  },
);

const styles = StyleSheet.create({
  applyButton: { backgroundColor: colors.primary, borderColor: colors.primary },
  applyLabel: { color: colors.surface, fontWeight: '700' },
  button: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    flex: 1,
    paddingVertical: spacing.md,
  },
  cancelButton: { backgroundColor: colors.surface, borderColor: colors.secondary },
  cancelLabel: { color: colors.secondary, fontWeight: '600' },
  footer: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.sm },
  list: { gap: spacing.sm },
  petName: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize,
    fontWeight: '600',
  },
  petRow: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
  sheet: {
    backgroundColor: colors.surface,
    gap: spacing.md,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
  },
  title: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', textAlign: 'center' },
});

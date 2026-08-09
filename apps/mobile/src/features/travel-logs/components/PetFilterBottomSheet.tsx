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
import { Button } from '@/src/components/ui/Button';
import { colors, radius, spacing, typography } from '@/src/theme';

import type { FilterSheetHandle } from './DateFilterBottomSheet';
import type { PetLogFilterOption } from '../utils/petFilterOptions';

type PetFilterBottomSheetProps = {
  /** 활성 프로필과 지워진 프로필(이전 프로필)을 함께 담은 목록 */
  options: PetLogFilterOption[];
  value: string[];
  onApply: (petIds: string[]) => void;
};

export const PetFilterBottomSheet = forwardRef<FilterSheetHandle, PetFilterBottomSheetProps>(
  function PetFilterBottomSheet({ options, value, onApply }, ref) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const [pendingPetIds, setPendingPetIds] = useState<string[]>(value);

    useImperativeHandle(
      ref,
      () => ({
        open: () => {
          // 시트를 다시 열 때 적용된 선택 상태를 그대로 복원한다.
          setPendingPetIds(value);
          sheetRef.current?.present();
        },
      }),
      [value],
    );

    const handleApply = useCallback(() => {
      onApply(pendingPetIds);
      sheetRef.current?.dismiss();
    }, [onApply, pendingPetIds]);

    const togglePet = useCallback((petId: string) => {
      setPendingPetIds((current) =>
        current.includes(petId) ? current.filter((id) => id !== petId) : [...current, petId],
      );
    }, []);

    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />
      ),
      [],
    );

    return (
      <BottomSheetModal backdropComponent={renderBackdrop} enablePanDownToClose ref={sheetRef}>
        <BottomSheetView style={styles.sheet}>
          <Text style={styles.title}>반려동물 선택</Text>

          <View style={styles.list}>
            {options.map((option) => {
              const selected = pendingPetIds.includes(option.petId);

              return (
                <Pressable
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  key={option.petId}
                  onPress={() => togglePet(option.petId)}
                  style={[
                    styles.petRow,
                    selected ? styles.petRowSelected : styles.petRowUnselected,
                  ]}
                >
                  <Avatar fallbackIcon="paw" size={40} uri={option.profileImage} />
                  <Text style={[styles.petName, option.isArchived && styles.archivedName]}>
                    {option.label}
                  </Text>
                  <Ionicons
                    color={selected ? colors.mintIcon : colors.border}
                    name={selected ? 'checkmark-circle' : 'ellipse-outline'}
                    size={22}
                  />
                </Pressable>
              );
            })}
          </View>

          <View style={styles.footer}>
            <View style={styles.footerButton}>
              <Button label="초기화" onPress={() => setPendingPetIds([])} variant="outline" />
            </View>
            <View style={styles.footerButton}>
              <Button label="적용" onPress={handleApply} variant="primary" />
            </View>
          </View>
        </BottomSheetView>
      </BottomSheetModal>
    );
  },
);

const styles = StyleSheet.create({
  archivedName: {
    color: colors.textSecondary,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  footerButton: {
    flex: 1,
  },
  list: {
    gap: spacing.sm,
  },
  petName: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize,
    fontWeight: '600',
  },
  petRow: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
  petRowSelected: {
    backgroundColor: colors.mintBg,
    borderColor: colors.mintIcon,
  },
  petRowUnselected: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
  },
  sheet: {
    backgroundColor: colors.background,
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});

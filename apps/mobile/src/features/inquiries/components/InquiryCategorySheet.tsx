import Ionicons from '@expo/vector-icons/Ionicons';
import {
  BottomSheetBackdrop,
  BottomSheetModal,
  BottomSheetView,
  type BottomSheetBackdropProps,
} from '@gorhom/bottom-sheet';
import { forwardRef, useCallback, useImperativeHandle, useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, radius, spacing, typography } from '@/src/theme';
import { INQUIRY_CATEGORY_OPTIONS, type InquiryCategory } from '@/src/types/inquiry';

export type InquiryCategorySheetHandle = { open: () => void };

type Props = {
  value?: InquiryCategory;
  onSelect: (category: InquiryCategory) => void;
};

export const InquiryCategorySheet = forwardRef<InquiryCategorySheetHandle, Props>(
  function InquiryCategorySheet({ value, onSelect }, ref) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const insets = useSafeAreaInsets();

    useImperativeHandle(ref, () => ({ open: () => sheetRef.current?.present() }), []);

    const dismiss = useCallback(() => sheetRef.current?.dismiss(), []);

    const handleSelect = useCallback(
      (category: InquiryCategory) => {
        onSelect(category);
        dismiss();
      },
      [dismiss, onSelect],
    );

    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop
          {...props}
          appearsOnIndex={0}
          disappearsOnIndex={-1}
          opacity={0.48}
          pressBehavior="close"
        />
      ),
      [],
    );

    return (
      <BottomSheetModal
        backdropComponent={renderBackdrop}
        enablePanDownToClose
        handleIndicatorStyle={styles.handle}
        ref={sheetRef}
      >
        <BottomSheetView
          style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}
        >
          <Text style={styles.title}>문의 유형</Text>
          <View style={styles.menu}>
            {INQUIRY_CATEGORY_OPTIONS.map((category) => {
              const isSelected = category === value;

              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: isSelected }}
                  key={category}
                  onPress={() => handleSelect(category)}
                  style={styles.menuRow}
                >
                  <Text style={[styles.menuLabel, isSelected && styles.menuLabelSelected]}>
                    {category}
                  </Text>
                  {isSelected ? (
                    <Ionicons color={colors.primary} name="checkmark" size={20} />
                  ) : null}
                </Pressable>
              );
            })}
          </View>
          <Pressable accessibilityRole="button" onPress={dismiss} style={styles.cancelButton}>
            <Text style={styles.cancelLabel}>취소</Text>
          </Pressable>
        </BottomSheetView>
      </BottomSheetModal>
    );
  },
);

const styles = StyleSheet.create({
  cancelButton: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 54,
  },
  cancelLabel: { color: colors.textPrimary, fontSize: typography.body.fontSize, fontWeight: '700' },
  handle: { backgroundColor: colors.border, width: 42 },
  menu: { borderBottomColor: colors.border, borderBottomWidth: 1 },
  menuLabel: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize,
    fontWeight: '500',
  },
  menuLabelSelected: {
    color: colors.primary,
    fontWeight: '700',
  },
  menuRow: {
    alignItems: 'center',
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: spacing.md,
    minHeight: 54,
    paddingHorizontal: spacing.sm,
  },
  sheet: {
    backgroundColor: colors.surface,
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xs,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
    paddingBottom: spacing.xs,
  },
});

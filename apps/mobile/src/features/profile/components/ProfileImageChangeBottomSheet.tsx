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

export type ProfileImageChangeBottomSheetHandle = { open: () => void };

type Props = {
  onSelectAlbum: () => Promise<void>;
  onResetToDefault: () => void;
  title?: string;
};

export const ProfileImageChangeBottomSheet = forwardRef<ProfileImageChangeBottomSheetHandle, Props>(
  function ProfileImageChangeBottomSheet(
    { onSelectAlbum, onResetToDefault, title = '프로필 이미지 변경' },
    ref,
  ) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const insets = useSafeAreaInsets();

    useImperativeHandle(ref, () => ({ open: () => sheetRef.current?.present() }), []);

    const dismiss = useCallback(() => sheetRef.current?.dismiss(), []);

    const runAction = useCallback(
      (action: () => Promise<void> | void) => {
        dismiss();
        void action();
      },
      [dismiss],
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
        <BottomSheetView style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}>
          <Text style={styles.title}>{title}</Text>
          <View style={styles.menu}>
            <ImageMenuRow
              icon="images-outline"
              label="앨범에서 선택"
              onPress={() => runAction(onSelectAlbum)}
            />
            <ImageMenuRow
              icon="refresh-outline"
              label="기본 이미지로 변경"
              onPress={() => runAction(onResetToDefault)}
            />
          </View>
          <Pressable accessibilityRole="button" onPress={dismiss} style={styles.cancelButton}>
            <Text style={styles.cancelLabel}>취소</Text>
          </Pressable>
        </BottomSheetView>
      </BottomSheetModal>
    );
  },
);

function ImageMenuRow({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.menuRow}>
      <Ionicons color={colors.sea} name={icon} size={24} />
      <Text style={styles.menuLabel}>{label}</Text>
      <Ionicons color={colors.textPrimary} name="chevron-forward" size={19} />
    </Pressable>
  );
}

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
  menuRow: {
    alignItems: 'center',
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: spacing.md,
    minHeight: 58,
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

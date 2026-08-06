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

export type PhotoChangeBottomSheetHandle = { open: () => void };

type Props = {
  onDelete: () => void;
  onSelectAlbum: () => Promise<void>;
  onTakePhoto: () => Promise<void>;
};

export const PhotoChangeBottomSheet = forwardRef<PhotoChangeBottomSheetHandle, Props>(
  function PhotoChangeBottomSheet({ onDelete, onSelectAlbum, onTakePhoto }, ref) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const insets = useSafeAreaInsets();

    useImperativeHandle(ref, () => ({ open: () => sheetRef.current?.present() }), []);

    const dismiss = useCallback(() => sheetRef.current?.dismiss(), []);
    const runPhotoAction = useCallback(
      (action: () => Promise<void>) => {
        dismiss();
        void action();
      },
      [dismiss],
    );
    const deletePhoto = useCallback(() => {
      dismiss();
      onDelete();
    }, [dismiss, onDelete]);
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
          <Text style={styles.title}>사진 변경</Text>
          <View style={styles.menu}>
            <PhotoMenuRow
              icon="camera-outline"
              label="카메라로 다시 촬영"
              onPress={() => runPhotoAction(onTakePhoto)}
            />
            <PhotoMenuRow
              icon="images-outline"
              label="앨범에서 다른 사진 선택"
              onPress={() => runPhotoAction(onSelectAlbum)}
            />
            <PhotoMenuRow
              destructive
              icon="trash-outline"
              label="사진 삭제"
              onPress={deletePhoto}
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

function PhotoMenuRow({
  destructive = false,
  icon,
  label,
  onPress,
}: {
  destructive?: boolean;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  const color = destructive ? colors.error : colors.mintIcon;

  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.menuRow}>
      <Ionicons color={color} name={icon} size={24} />
      <Text style={[styles.menuLabel, destructive && styles.deleteLabel]}>{label}</Text>
      <Ionicons color={destructive ? colors.error : colors.textPrimary} name="chevron-forward" size={19} />
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
  deleteLabel: { color: colors.error },
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

import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type PlaceSearchBarProps = {
  value: string;
  onChangeValue: (value: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  onPressBack: () => void;
  /** 검색 결과를 보고 있는 중인지 (지우기 버튼 노출 기준) */
  isSearching: boolean;
};

/** 지도 위에 떠 있는 검색 바 */
export function PlaceSearchBar({
  value,
  onChangeValue,
  onSubmit,
  onClear,
  onPressBack,
  isSearching,
}: PlaceSearchBarProps) {
  const canClear = value.length > 0 || isSearching;

  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityLabel="뒤로 가기"
        accessibilityRole="button"
        hitSlop={spacing.sm}
        onPress={onPressBack}
      >
        <Ionicons color={colors.basalt} name="chevron-back" size={22} />
      </Pressable>

      <TextInput
        onChangeText={onChangeValue}
        onSubmitEditing={onSubmit}
        placeholder="관광지/맛집/숙소 검색"
        placeholderTextColor={colors.textTertiary}
        returnKeyType="search"
        style={styles.input}
        value={value}
      />

      {canClear && (
        <Pressable
          accessibilityLabel="검색어 지우기"
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onClear}
        >
          <Ionicons color={colors.textTertiary} name="close-circle" size={18} />
        </Pressable>
      )}

      <Pressable
        accessibilityLabel="검색"
        accessibilityRole="button"
        hitSlop={spacing.sm}
        onPress={onSubmit}
      >
        <Ionicons color={colors.basalt} name="search" size={20} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    elevation: 3,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 4,
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.14,
    shadowRadius: 8,
  },
  input: {
    color: colors.basalt,
    flex: 1,
    fontSize: typography.body.fontSize - 1,
    padding: 0,
  },
});

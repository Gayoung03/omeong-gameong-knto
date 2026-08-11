import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type TravelLogFilterBarProps = {
  searchInput: string;
  onChangeSearch: (value: string) => void;
  onOpenDateFilter: () => void;
  onOpenPetFilter: () => void;
  isDateFilterActive: boolean;
  isPetFilterActive: boolean;
  /** 등록된 반려동물이 2마리 이상일 때만 반려동물 필터를 노출한다. */
  showPetFilter: boolean;
};

export function TravelLogFilterBar({
  searchInput,
  onChangeSearch,
  onOpenDateFilter,
  onOpenPetFilter,
  isDateFilterActive,
  isPetFilterActive,
  showPetFilter,
}: TravelLogFilterBarProps) {
  return (
    <View style={styles.row}>
      <View style={styles.searchBox}>
        <Ionicons color={colors.iconGray} name="search" size={18} />
        <TextInput
          accessibilityLabel="장소명 검색"
          onChangeText={onChangeSearch}
          placeholder="장소명을 검색해 주세요"
          placeholderTextColor={colors.textSecondary}
          returnKeyType="search"
          style={styles.input}
          value={searchInput}
        />
        {searchInput.length > 0 ? (
          <Pressable
            accessibilityLabel="검색어 지우기"
            accessibilityRole="button"
            hitSlop={spacing.sm}
            onPress={() => onChangeSearch('')}
          >
            <Ionicons color={colors.iconGray} name="close-circle" size={18} />
          </Pressable>
        ) : null}
      </View>

      <FilterIconButton
        accessibilityLabel="날짜 필터"
        active={isDateFilterActive}
        activeBackground={colors.primarySoft}
        activeForeground={colors.primary}
        icon="calendar-outline"
        onPress={onOpenDateFilter}
      />

      {showPetFilter ? (
        <FilterIconButton
          accessibilityLabel="반려동물 필터"
          active={isPetFilterActive}
          activeBackground={colors.seaSoftLight}
          activeForeground={colors.sea}
          icon="paw-outline"
          onPress={onOpenPetFilter}
        />
      ) : null}
    </View>
  );
}

type FilterIconButtonProps = {
  icon: keyof typeof Ionicons.glyphMap;
  accessibilityLabel: string;
  active: boolean;
  activeBackground: string;
  activeForeground: string;
  onPress: () => void;
};

function FilterIconButton({
  icon,
  accessibilityLabel,
  active,
  activeBackground,
  activeForeground,
  onPress,
}: FilterIconButtonProps) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={[
        styles.filterButton,
        active
          ? { backgroundColor: activeBackground, borderColor: activeForeground }
          : { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <Ionicons color={active ? activeForeground : colors.iconGray} name={icon} size={20} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  filterButton: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  input: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
    padding: 0,
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  searchBox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    height: 44,
    paddingHorizontal: spacing.sm + spacing.xs,
  },
});

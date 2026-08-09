import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

import type { QuickMenuItem } from '../types/home';
import { SectionHeader } from './SectionHeader';

type QuickMenuProps = {
  items: QuickMenuItem[];
  onPressItem: (item: QuickMenuItem) => void;
};

export function QuickMenu({ items, onPressItem }: QuickMenuProps) {
  return (
    <View>
      <SectionHeader title="빠른 메뉴" />
      <View style={styles.grid}>
        {items.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onPressItem(item)}
            style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
          >
            <View style={[styles.iconCircle, { backgroundColor: item.iconBackgroundColor }]}>
              <Ionicons color={item.iconColor} name={item.icon} size={22} />
            </View>
            <View style={styles.copy}>
              <Text numberOfLines={1} style={styles.title}>
                {item.title}
              </Text>
              <Text numberOfLines={1} style={styles.subtitle}>
                {item.subtitle}
              </Text>
            </View>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  menuItem: {
    width: '48.5%',
    minHeight: 74,
    paddingHorizontal: 8,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    borderWidth: 1,
    borderColor: '#F0F0F0',
    borderRadius: 16,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.6,
    transform: [{ scale: 0.98 }],
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  subtitle: {
    marginTop: 3,
    color: colors.textSecondary,
    fontSize: 10,
  },
});

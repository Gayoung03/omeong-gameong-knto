import Ionicons from '@expo/vector-icons/Ionicons';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { appNotifications } from '@/src/features/notifications/mocks/notification.mock';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

/** 팝업은 최신 알림 몇 건만 보여준다. 전체 목록은 `/notifications` 화면에 있다. */
const PREVIEW_COUNT = 2;

type Props = {
  visible: boolean;
  onClose: () => void;
};

/**
 * 상단 바의 알림 간이 보기.
 *
 * 홈·마이페이지처럼 알림 화면(`/notifications`)으로 보내는 대신,
 * 작업 흐름이 끊기면 안 되는 화면에서 겹쳐 띄운다.
 */
export function NotificationPopup({ visible, onClose }: Props) {
  return (
    <Modal animationType="fade" onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <Pressable accessibilityLabel="닫기" onPress={onClose} style={styles.dismissArea} />

        <View style={styles.card}>
          <View style={styles.header}>
            <Text style={styles.title}>알림</Text>
            <Pressable accessibilityLabel="닫기" hitSlop={10} onPress={onClose}>
              <Ionicons color={colors.textSecondary} name="close" size={23} />
            </Pressable>
          </View>

          <View style={styles.list}>
            {appNotifications.slice(0, PREVIEW_COUNT).map((item) => (
              <View key={item.id} style={styles.item}>
                <View style={[styles.icon, item.tone === 'sea' && styles.iconSea]}>
                  <Ionicons
                    color={item.tone === 'sea' ? colors.sea : colors.primary}
                    name={item.icon}
                    size={19}
                  />
                </View>
                <View style={styles.itemCopy}>
                  <Text style={styles.itemTitle}>{item.title}</Text>
                  <Text style={styles.itemText}>{item.description}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const ICON_SIZE = 38;

const styles = StyleSheet.create({
  backdrop: {
    alignItems: 'center',
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'center',
    padding: spacing.md,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    maxWidth: 398,
    padding: spacing.md,
    width: '100%',
  },
  dismissArea: {
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  icon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: ICON_SIZE / 2,
    height: ICON_SIZE,
    justifyContent: 'center',
    width: ICON_SIZE,
  },
  iconSea: {
    backgroundColor: colors.seaSoftLight,
  },
  item: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
  itemCopy: {
    flex: 1,
  },
  itemText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 17,
    marginTop: 3,
  },
  itemTitle: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  list: {
    gap: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '800',
  },
});

import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, spacing, typography } from '@/src/theme';

import { legalDocuments, type LegalDocumentId } from '../constants/legalDocuments';

const ICON_BUTTON_TOUCH_SIZE = 44;

export function LegalDocumentScreen({ documentId }: { documentId: LegalDocumentId }) {
  const router = useRouter();
  const document = legalDocuments[documentId];

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <IconButton
          accessibilityLabel="뒤로 가기"
          icon="chevron-back"
          onPress={() => router.back()}
        />
        <Text style={styles.title}>{document.title}</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.body}>{document.content}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  body: {
    color: colors.textStrong,
    fontSize: typography.body.fontSize,
    lineHeight: 26,
  },
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.md,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  spacer: {
    height: ICON_BUTTON_TOUCH_SIZE,
    width: ICON_BUTTON_TOUCH_SIZE,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize,
    fontWeight: typography.title.fontWeight,
  },
});

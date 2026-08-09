import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, radius, spacing, typography } from '@/src/theme';
import { INQUIRY_STATUS_LABEL, type InquiryItem } from '@/src/types/inquiry';

import { InquiryCard } from './components/InquiryCard';
import { InquiryFilterTabs, type InquiryFilter } from './components/InquiryFilterTabs';
import {
  InquiryEmptyState,
  InquiryErrorState,
  InquiryNoResultsState,
} from './components/InquiryStates';
import { useInquiries } from './hooks/useInquiries';

export function InquiryListScreen() {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useInquiries();
  const [filter, setFilter] = useState<InquiryFilter>('all');

  const inquiries = useMemo(() => data ?? [], [data]);
  const filteredInquiries = useMemo(
    () => (filter === 'all' ? inquiries : inquiries.filter((item) => item.status === filter)),
    [filter, inquiries],
  );

  const goToCreate = () => router.push('/inquiries/new');

  const renderEmptyContent = () => {
    // 로딩 중에는 빈 상태 문구가 잠깐 스쳐 지나가지 않도록 아무것도 그리지 않는다.
    if (isPending) return null;
    if (isError) return <InquiryErrorState onRetry={() => refetch()} />;
    if (inquiries.length === 0) return <InquiryEmptyState onCreate={goToCreate} />;
    if (filter !== 'all') return <InquiryNoResultsState statusLabel={INQUIRY_STATUS_LABEL[filter]} />;

    return null;
  };

  const renderItem = ({ item }: { item: InquiryItem }) => (
    <InquiryCard inquiry={item} onPress={() => router.push(`/inquiries/${item.id}`)} />
  );

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="1:1 문의" />
      <FlatList
        contentContainerStyle={styles.content}
        data={isPending || isError ? [] : filteredInquiries}
        keyExtractor={(item) => item.id}
        ListEmptyComponent={renderEmptyContent()}
        ListHeaderComponent={
          <View style={styles.listHeader}>
            <Text style={styles.guide}>
              궁금한 점이나 불편한 점을 남겨주세요.{'\n'}확인 후 답변해드릴게요.
            </Text>
            <Pressable
              accessibilityLabel="새 문의 작성"
              accessibilityRole="button"
              onPress={goToCreate}
              style={({ pressed }) => [styles.createButton, pressed && styles.createButtonPressed]}
            >
              <Text style={styles.createButtonLabel}>+ 새 문의 작성</Text>
            </Pressable>
            <InquiryFilterTabs onChange={setFilter} value={filter} />
          </View>
        }
        renderItem={renderItem}
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  // 목록 상단의 새 문의 작성 버튼: 이 화면에서만 쓰는 아웃라인 스타일
  createButton: {
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderRadius: radius.md,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  createButtonLabel: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: '600',
  },
  createButtonPressed: {
    opacity: 0.7,
  },
  guide: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
    textAlign: 'center',
  },
  listHeader: {
    gap: spacing.lg,
    paddingBottom: spacing.xs,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});

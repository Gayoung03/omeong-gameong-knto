import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { NoticeAccordionItem } from './components/NoticeAccordionItem';
import { fetchNotice, fetchNotices } from './api/noticeApi';

export function NoticeScreen() {
  // 한 번에 하나만 열린다. null이면 전부 접힌 상태.
  const [expandedNoticeId, setExpandedNoticeId] = useState<string | null>(null);
  const { data: notices = [] } = useQuery({ queryKey: ['notices'], queryFn: fetchNotices });
  const { data: expandedNotice } = useQuery({
    queryKey: ['notices', expandedNoticeId],
    queryFn: () => fetchNotice(expandedNoticeId!),
    enabled: expandedNoticeId !== null,
  });

  const handleNoticePress = (noticeId: string) => {
    setExpandedNoticeId((currentId) => (currentId === noticeId ? null : noticeId));
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="공지사항" />
      <ScrollView contentContainerStyle={styles.content}>
        {notices.map((notice) => (
          <NoticeAccordionItem
            isExpanded={notice.id === expandedNoticeId}
            key={notice.id}
            notice={notice.id === expandedNoticeId && expandedNotice ? expandedNotice : notice}
            onPress={() => handleNoticePress(notice.id)}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});

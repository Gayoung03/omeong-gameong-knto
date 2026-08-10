import Ionicons from '@expo/vector-icons/Ionicons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card } from '@/src/components/ui/Card';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { formatShortDate } from '@/src/features/travel-logs/utils/dateFormat';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { InquiryItem } from '@/src/types/inquiry';

import { InquiryStatusBadge } from './components/InquiryStatusBadge';
import { InquiryErrorState } from './components/InquiryStates';
import { useInquiry } from './hooks/useInquiries';

const THUMBNAIL_SIZE = 120;

type Props = {
  inquiryId: string;
};

export function InquiryDetailScreen({ inquiryId }: Props) {
  const { data: inquiry, isPending, isError, refetch } = useInquiry(inquiryId);

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="문의 상세" />
      <ScrollView contentContainerStyle={styles.content}>
        {isError ? <InquiryErrorState onRetry={() => refetch()} /> : null}
        {/* 로딩 중에는 잠깐 빈 화면을 두고, 도착하면 한 번에 그린다. */}
        {!isPending && !isError && inquiry ? <InquiryDetailBody inquiry={inquiry} /> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function InquiryDetailBody({ inquiry }: { inquiry: InquiryItem }) {
  const isAnswered = inquiry.status === 'completed';

  return (
    <>
      <View style={styles.summary}>
        <InquiryStatusBadge status={inquiry.status} />
        <Text style={styles.title}>{inquiry.title}</Text>
        <Text style={styles.meta}>
          {inquiry.category} · {formatShortDate(inquiry.createdAt)}
        </Text>
      </View>

      <Card padding="lg" style={styles.card}>
        <Text style={[styles.sectionTitle, styles.questionTitle]}>내 문의</Text>
        <Text style={styles.body}>{inquiry.content}</Text>

        {inquiry.images?.length ? (
          <View style={styles.attachments}>
            <View style={styles.divider} />
            <Text style={styles.attachmentLabel}>첨부 이미지</Text>
            <View style={styles.thumbnailRow}>
              {inquiry.images.map((uri) => (
                <RemoteImage
                  borderRadius={radius.md}
                  key={uri}
                  style={styles.thumbnail}
                  uri={uri}
                />
              ))}
            </View>
          </View>
        ) : null}
      </Card>

      <Card padding="lg" style={styles.card}>
        <View style={styles.answerHeader}>
          <Text style={[styles.sectionTitle, styles.answerTitle]}>오멍가멍 답변</Text>
          {isAnswered ? (
            <View style={styles.answerCheck}>
              <Ionicons color={colors.sea} name="checkmark" size={16} />
            </View>
          ) : null}
        </View>
        <Text style={[styles.body, !isAnswered && styles.pendingBody]}>
          {isAnswered
            ? inquiry.answer
            : '문의 내용을 확인하고 있어요.\n답변이 등록되면 알려드릴게요.'}
        </Text>
      </Card>

      {isAnswered && inquiry.answeredAt ? (
        <View style={styles.answeredChip}>
          <Ionicons color={colors.textSecondary} name="calendar-outline" size={14} />
          <Text style={styles.answeredLabel}>답변 등록 {formatShortDate(inquiry.answeredAt)}</Text>
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  answerCheck: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderRadius: 9999,
    height: 26,
    justifyContent: 'center',
    width: 26,
  },
  answerHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  answerTitle: {
    color: colors.sea,
  },
  answeredChip: {
    alignItems: 'center',
    alignSelf: 'center',
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  answeredLabel: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  attachmentLabel: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  attachments: {
    gap: spacing.sm,
  },
  body: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    lineHeight: 24,
  },
  card: {
    gap: spacing.md,
  },
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  divider: {
    backgroundColor: colors.border,
    height: 1,
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  pendingBody: {
    color: colors.textSecondary,
  },
  questionTitle: {
    color: colors.primary,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  sectionTitle: {
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  summary: {
    gap: spacing.sm,
    paddingBottom: spacing.xs,
  },
  thumbnail: {
    height: THUMBNAIL_SIZE,
    width: THUMBNAIL_SIZE,
  },
  thumbnailRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize - 2,
    fontWeight: '700',
    lineHeight: 28,
  },
});

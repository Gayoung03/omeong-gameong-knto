import Ionicons from '@expo/vector-icons/Ionicons';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { categoryColors, colors, radius, shadow, spacing, typography } from '@/src/theme';

import {
  type GuideBadge,
  type GuideTone,
  type TransportGuide,
} from '../constants/travelGuideContent';
import { useTravelGuideDetail } from '../hooks/useTravelGuides';

type TravelGuideDetailScreenProps = {
  guideId: string;
};

const toneStyles: Record<
  GuideTone,
  { backgroundColor: string; borderColor: string; textColor: string }
> = {
  orange: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoftStrong,
    textColor: colors.primaryDeep,
  },
  mint: {
    backgroundColor: colors.seaSoftLight,
    borderColor: colors.seaSoft,
    textColor: colors.seaDeep,
  },
  green: {
    backgroundColor: colors.leafSoft,
    borderColor: categoryColors.leaf.bg,
    textColor: colors.leaf,
  },
  blue: {
    backgroundColor: categoryColors.blue.bg,
    borderColor: categoryColors.blue.bg,
    textColor: categoryColors.blue.fg,
  },
  warning: {
    backgroundColor: colors.errorBg,
    borderColor: colors.errorBg,
    textColor: colors.error,
  },
  neutral: {
    backgroundColor: colors.neutralGray,
    borderColor: colors.border,
    textColor: colors.textStrong,
  },
};

export function TravelGuideDetailScreen({ guideId }: TravelGuideDetailScreenProps) {
  const { data: guide, error, isError, isPending, refetch } = useTravelGuideDetail(guideId);

  if (isPending) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <ScreenHeader title="여행 가이드" />
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (isError) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <ScreenHeader title="여행 가이드" />
        <ErrorState error={error} onRetry={() => refetch()} />
      </SafeAreaView>
    );
  }

  if (!guide) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <ScreenHeader title="여행 가이드" />
        <EmptyState
          description="가이드 목록에서 다시 선택해 주세요."
          icon="document-text-outline"
          title="가이드를 찾을 수 없어요"
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title={`${guide.carrierName} 규정`} />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <DetailHero guide={guide} />
        <OfficialNotice />
        <FactSection guide={guide} />
        <NoteSection guide={guide} />
        <SourceSection guide={guide} />
      </ScrollView>
    </SafeAreaView>
  );
}

function DetailHero({ guide }: { guide: TransportGuide }) {
  const iconColor = guide.category === 'airline' ? colors.seaDeep : colors.leaf;
  const iconBackground = guide.category === 'airline' ? colors.seaSoftLight : colors.leafSoft;

  return (
    <View style={styles.hero}>
      <View style={[styles.heroIcon, { backgroundColor: iconBackground }]}>
        <Ionicons color={iconColor} name={guide.icon} size={26} />
      </View>
      <View style={styles.heroCopy}>
        <Text style={styles.heroEyebrow}>
          {guide.category === 'airline' ? '항공사 규정' : guide.route}
        </Text>
        <Text style={styles.heroTitle}>{guide.carrierName}</Text>
        <Text style={styles.heroDescription}>{guide.summary}</Text>
      </View>
      <BadgeRow badges={guide.badges} />
    </View>
  );
}

function OfficialNotice() {
  return (
    <View style={styles.notice}>
      <Ionicons color={colors.primary} name="alert-circle" size={18} />
      <Text style={styles.noticeText}>예약 전 공식 페이지에서 최신 규정을 다시 확인해 주세요.</Text>
    </View>
  );
}

function FactSection({ guide }: { guide: TransportGuide }) {
  return (
    <View style={styles.sectionCard}>
      <SectionTitle icon="list-outline" title="핵심 정보" />
      <View style={styles.factList}>
        {guide.facts.map((fact) => (
          <View key={fact.label} style={styles.factRow}>
            <Text style={styles.factLabel}>{fact.label}</Text>
            <Text style={styles.factValue}>{fact.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function NoteSection({ guide }: { guide: TransportGuide }) {
  return (
    <View style={styles.sectionCard}>
      <SectionTitle icon="shield-checkmark-outline" title="꼭 확인할 것" />
      {guide.warning ? (
        <View style={styles.warningBox}>
          <Ionicons color={colors.error} name="warning-outline" size={16} />
          <Text style={styles.warningText}>{guide.warning}</Text>
        </View>
      ) : null}
      <View style={styles.noteList}>
        {guide.notes.map((note) => (
          <View key={note} style={styles.noteRow}>
            <Ionicons color={colors.seaDeep} name="checkmark-circle" size={15} />
            <Text style={styles.noteText}>{note}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function SourceSection({ guide }: { guide: TransportGuide }) {
  return (
    <View style={styles.sourceCard}>
      <View style={styles.sourceRow}>
        <Ionicons color={colors.iconGray} name="calendar-outline" size={16} />
        <Text style={styles.sourceLabel}>확인일</Text>
        <Text style={styles.sourceValue}>{guide.verifiedLabel}</Text>
      </View>
      <View style={styles.sourceRow}>
        <Ionicons color={colors.iconGray} name="document-text-outline" size={16} />
        <Text style={styles.sourceLabel}>출처</Text>
        <Text numberOfLines={2} style={styles.sourceValue}>
          {guide.sourceLabel}
        </Text>
      </View>
    </View>
  );
}

function SectionTitle({ icon, title }: { icon: keyof typeof Ionicons.glyphMap; title: string }) {
  return (
    <View style={styles.sectionTitleRow}>
      <View style={styles.sectionIcon}>
        <Ionicons color={colors.seaDeep} name={icon} size={17} />
      </View>
      <Text style={styles.sectionTitle}>{title}</Text>
    </View>
  );
}

function BadgeRow({ badges }: { badges: GuideBadge[] }) {
  return (
    <View style={styles.badgeRow}>
      {badges.map((badge) => (
        <View
          key={`${badge.label}-${badge.tone}`}
          style={[
            styles.badge,
            {
              backgroundColor: toneStyles[badge.tone].backgroundColor,
              borderColor: toneStyles[badge.tone].borderColor,
            },
          ]}
        >
          <Text style={[styles.badgeText, { color: toneStyles[badge.tone].textColor }]}>
            {badge.label}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 1,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  badgeText: {
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xl,
  },
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  factLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    width: 86,
  },
  factList: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    overflow: 'hidden',
  },
  factRow: {
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  factValue: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
    lineHeight: 19,
    textAlign: 'right',
  },
  hero: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md,
    ...shadow.sm,
  },
  heroCopy: {
    gap: spacing.xs,
  },
  heroDescription: {
    color: colors.textStrong,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    lineHeight: 20,
  },
  heroEyebrow: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
  },
  heroIcon: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 52,
    justifyContent: 'center',
    width: 52,
  },
  heroTitle: {
    color: colors.textPrimary,
    fontSize: 24,
    fontWeight: '800',
    lineHeight: 30,
  },
  noteList: {
    gap: spacing.sm,
  },
  noteRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  noteText: {
    color: colors.textStrong,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    lineHeight: 20,
  },
  notice: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoftStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  noticeText: {
    color: colors.primaryDeep,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
    lineHeight: 19,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  sectionCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md,
    ...shadow.sm,
  },
  sectionIcon: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderRadius: radius.full,
    height: 30,
    justifyContent: 'center',
    width: 30,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '800',
  },
  sectionTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  sourceCard: {
    backgroundColor: colors.neutralGray,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  sourceLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
    width: 44,
  },
  sourceRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  sourceValue: {
    color: colors.textStrong,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
    lineHeight: 19,
    textAlign: 'right',
  },
  warningBox: {
    alignItems: 'flex-start',
    backgroundColor: colors.errorBg,
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.xs,
    padding: spacing.sm,
  },
  warningText: {
    color: colors.error,
    flex: 1,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
    lineHeight: 17,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { brandAssets } from '@/src/config/brandAssets';
import { categoryColors, colors, radius, shadow, spacing, typography } from '@/src/theme';
import type { IoniconName } from '@/src/features/home/types/home';

import {
  checklistSections,
  type ChecklistItem,
  type GuideBadge,
  type GuideTone,
  type PreparationGuide,
  type TransportGuide,
} from '../constants/travelGuideContent';
import { useTravelGuideOverview } from '../hooks/useTravelGuides';

type GuideTab = 'airline' | 'ferry' | 'checklist';

type GuideTabItem = {
  id: GuideTab;
  label: string;
  countLabel: string;
  icon: IoniconName;
};

const GUIDE_TABS: GuideTabItem[] = [
  { id: 'airline', label: '항공', countLabel: '0', icon: 'airplane' },
  { id: 'ferry', label: '여객선', countLabel: '0', icon: 'boat' },
  { id: 'checklist', label: '체크리스트', countLabel: '0', icon: 'checkmark-circle-outline' },
];

const tabCopy: Record<GuideTab, { title: string; description: string }> = {
  airline: {
    title: '항공사별 필수 규정',
    description: '기내 무게, 위탁 가능 여부, 요금, 신청 조건을 먼저 비교해요.',
  },
  ferry: {
    title: '여객선 항로별 필수 규정',
    description: '항로, 소요 시간, 객실 조건, 케이지 시간을 함께 봐요.',
  },
  checklist: {
    title: '출발 전 공통 체크',
    description: '운송사 규정에서 반복되는 준비 항목을 여행 전에 점검해요.',
  },
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

export function TravelPreparationScreen() {
  const [activeTab, setActiveTab] = useState<GuideTab>('airline');
  const [checkedIds, setCheckedIds] = useState<Set<string>>(() => new Set());
  const { data, error, isError, isPending, refetch } = useTravelGuideOverview();

  const checklistTotal = checklistSections.reduce(
    (count, section) => count + section.items.length,
    0,
  );
  const checklistProgress = checklistTotal > 0 ? checkedIds.size / checklistTotal : 0;
  const tabCounts: Record<GuideTab, number> = {
    airline: data?.airlineGuides.length ?? 0,
    ferry: data?.ferryGuides.length ?? 0,
    checklist: checklistSections.length,
  };

  const handleTabPress = (tab: GuideTab) => {
    setActiveTab(tab);
  };

  const openTransportGuide = (guideId: string) => {
    router.push({
      pathname: '/travel-guides/[guideId]',
      params: { guideId },
    });
  };

  const toggleChecklistItem = (itemId: string) => {
    setCheckedIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="여행 준비 가이드" />
      {isPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <GuideHero
            guideCount={data.guideCount}
            latestVerifiedLabel={data.latestVerifiedLabel}
            ruleCount={data.ruleCount}
          />
          <OfficialNotice />
          <GuideTabBar activeTab={activeTab} counts={tabCounts} onPressTab={handleTabPress} />

          <View style={styles.sectionIntro}>
            <Text style={styles.sectionTitle}>{tabCopy[activeTab].title}</Text>
            <Text style={styles.sectionDescription}>{tabCopy[activeTab].description}</Text>
          </View>

          {activeTab === 'airline' ? (
            <TransportGuideList guides={data.airlineGuides} onPressGuide={openTransportGuide} />
          ) : null}

          {activeTab === 'ferry' ? (
            <TransportGuideList guides={data.ferryGuides} onPressGuide={openTransportGuide} />
          ) : null}

          {activeTab === 'checklist' ? (
            <ChecklistGuide
              checkedIds={checkedIds}
              checkedTotal={checkedIds.size}
              progress={checklistProgress}
              preparationGuides={data.preparationGuides}
              total={checklistTotal}
              onToggleItem={toggleChecklistItem}
            />
          ) : null}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function GuideHero({
  guideCount,
  latestVerifiedLabel,
  ruleCount,
}: {
  guideCount: number;
  latestVerifiedLabel: string;
  ruleCount: number;
}) {
  return (
    <View style={styles.hero}>
      <View style={styles.heroCopy}>
        <Text style={styles.heroEyebrow}>공식 안내 기반</Text>
        <Text style={styles.heroTitle}>반려동물과 제주까지</Text>
        <Text style={styles.heroDescription}>
          항공사와 여객선 규정, 출발 전 체크 항목을 한곳에서 확인해요.
        </Text>
      </View>
      <Image resizeMode="contain" source={brandAssets.character.sitting} style={styles.heroImage} />

      <View style={styles.heroStats}>
        <SummaryItem label="가이드" value={`${guideCount}편`} />
        <SummaryItem label="운송 규정" value={`${ruleCount}건`} />
        <SummaryItem label="확인일" value={latestVerifiedLabel} />
      </View>
    </View>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryItem}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
    </View>
  );
}

function OfficialNotice() {
  return (
    <View style={styles.notice}>
      <View style={styles.noticeIcon}>
        <Ionicons color={colors.primary} name="alert-circle-outline" size={18} />
      </View>
      <View style={styles.noticeCopy}>
        <Text style={styles.noticeTitle}>예약 전 공식 페이지 재확인</Text>
        <Text style={styles.noticeDescription}>
          요금, 기종, 계절 제한, 견종 제한은 출발 전 한 번 더 확인해 주세요.
        </Text>
      </View>
    </View>
  );
}

function GuideTabBar({
  activeTab,
  counts,
  onPressTab,
}: {
  activeTab: GuideTab;
  counts: Record<GuideTab, number>;
  onPressTab: (tab: GuideTab) => void;
}) {
  return (
    <View style={styles.tabBar}>
      {GUIDE_TABS.map((tab) => {
        const isSelected = tab.id === activeTab;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={tab.id}
            onPress={() => onPressTab(tab.id)}
            style={[styles.tabItem, isSelected && styles.tabItemSelected]}
          >
            <Ionicons
              color={isSelected ? colors.primary : colors.iconGray}
              name={tab.icon}
              size={17}
            />
            <Text style={[styles.tabLabel, isSelected && styles.tabLabelSelected]}>
              {tab.label}
            </Text>
            <Text style={[styles.tabCount, isSelected && styles.tabCountSelected]}>
              {counts[tab.id] || tab.countLabel}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function TransportGuideList({
  guides,
  onPressGuide,
}: {
  guides: TransportGuide[];
  onPressGuide: (guideId: string) => void;
}) {
  return (
    <View style={styles.guideList}>
      {guides.map((guide) => (
        <TransportGuideCard guide={guide} key={guide.id} onPress={() => onPressGuide(guide.id)} />
      ))}
    </View>
  );
}

function TransportGuideCard({ guide, onPress }: { guide: TransportGuide; onPress: () => void }) {
  const iconTone = guide.category === 'airline' ? colors.seaDeep : colors.leaf;
  const iconBackground = guide.category === 'airline' ? colors.seaSoftLight : colors.leafSoft;

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.ruleCard, pressed && styles.pressed]}
    >
      <View style={styles.ruleHeader}>
        <View style={[styles.ruleIcon, { backgroundColor: iconBackground }]}>
          <Ionicons color={iconTone} name={guide.icon} size={21} />
        </View>
        <View style={styles.ruleTitleBlock}>
          <Text style={styles.ruleTitle}>{guide.carrierName}</Text>
          <Text numberOfLines={1} style={styles.ruleSubtitle}>
            {guide.route ?? guide.verifiedLabel}
          </Text>
        </View>
        <View style={styles.ruleMeta}>
          <Text style={styles.verifiedLabel}>{guide.verifiedLabel}</Text>
          <Ionicons color={colors.textSecondary} name="chevron-forward" size={18} />
        </View>
      </View>

      <Text style={styles.ruleSummary}>{guide.summary}</Text>
      <BadgeRow badges={guide.badges} />
    </Pressable>
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

function ChecklistGuide({
  checkedIds,
  checkedTotal,
  preparationGuides,
  progress,
  total,
  onToggleItem,
}: {
  checkedIds: Set<string>;
  checkedTotal: number;
  preparationGuides: PreparationGuide[];
  progress: number;
  total: number;
  onToggleItem: (itemId: string) => void;
}) {
  return (
    <View style={styles.checklistContent}>
      <View style={styles.progressCard}>
        <View style={styles.progressHeader}>
          <View>
            <Text style={styles.progressTitle}>공통 체크 진행률</Text>
            <Text style={styles.progressDescription}>
              예약, 케이지, 당일 준비를 차례로 점검해요.
            </Text>
          </View>
          <Text style={styles.progressCount}>
            {checkedTotal}/{total}
          </Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${Math.round(progress * 100)}%` }]} />
        </View>
      </View>

      {checklistSections.map((section) => (
        <ChecklistSectionBlock
          checkedIds={checkedIds}
          key={section.id}
          section={section}
          onToggleItem={onToggleItem}
        />
      ))}

      <View style={styles.readingSection}>
        <Text style={styles.readingTitle}>함께 읽으면 좋은 준비 가이드</Text>
        <View style={styles.preparationList}>
          {preparationGuides.map((guide) => (
            <PreparationGuideCard guide={guide} key={guide.id} />
          ))}
        </View>
      </View>
    </View>
  );
}

function ChecklistSectionBlock({
  checkedIds,
  section,
  onToggleItem,
}: {
  checkedIds: Set<string>;
  section: (typeof checklistSections)[number];
  onToggleItem: (itemId: string) => void;
}) {
  const checkedCount = section.items.filter((item) => checkedIds.has(item.id)).length;

  return (
    <View style={styles.checkSection}>
      <View style={styles.checkSectionHeader}>
        <View style={styles.checkSectionTitleRow}>
          <View style={styles.checkSectionIcon}>
            <Ionicons color={colors.leaf} name={section.icon} size={18} />
          </View>
          <Text style={styles.checkSectionTitle}>{section.title}</Text>
        </View>
        <Text style={styles.checkSectionCount}>
          {checkedCount}/{section.items.length}
        </Text>
      </View>

      {section.items.map((item) => (
        <ChecklistTaskRow
          isChecked={checkedIds.has(item.id)}
          item={item}
          key={item.id}
          onToggle={() => onToggleItem(item.id)}
        />
      ))}
    </View>
  );
}

function ChecklistTaskRow({
  isChecked,
  item,
  onToggle,
}: {
  isChecked: boolean;
  item: ChecklistItem;
  onToggle: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: isChecked }}
      onPress={onToggle}
      style={({ pressed }) => [styles.taskRow, pressed && styles.pressed]}
    >
      <View style={[styles.checkbox, isChecked && styles.checkboxChecked]}>
        {isChecked ? <Ionicons color={colors.surface} name="checkmark" size={14} /> : null}
      </View>
      <View style={styles.taskCopy}>
        <Text style={[styles.taskLabel, isChecked && styles.taskLabelChecked]}>{item.label}</Text>
        <Text style={styles.taskHint}>{item.hint}</Text>
      </View>
    </Pressable>
  );
}

function PreparationGuideCard({ guide }: { guide: PreparationGuide }) {
  return (
    <View style={styles.prepCard}>
      <View style={styles.prepHeader}>
        <View style={styles.prepIcon}>
          <Ionicons color={colors.primaryDeep} name={guide.icon} size={18} />
        </View>
        <View style={styles.prepTitleBlock}>
          <Text style={styles.prepTitle}>{guide.title}</Text>
          <Text style={styles.prepVerified}>{guide.verifiedLabel}</Text>
        </View>
      </View>
      <Text style={styles.prepDescription}>{guide.description}</Text>
      <BadgeRow badges={guide.badges} />
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
  checkbox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm - 1,
    borderWidth: 1.6,
    height: 22,
    justifyContent: 'center',
    width: 22,
  },
  checkboxChecked: {
    backgroundColor: colors.sea,
    borderColor: colors.sea,
  },
  checkSection: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: 'hidden',
    ...shadow.sm,
  },
  checkSectionCount: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  checkSectionHeader: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  checkSectionIcon: {
    alignItems: 'center',
    backgroundColor: colors.leafSoft,
    borderRadius: radius.full,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  checkSectionTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '700',
  },
  checkSectionTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  checklistContent: {
    gap: spacing.md,
  },
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  guideList: {
    gap: spacing.md,
  },
  hero: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoftStrong,
    borderRadius: radius.xl,
    borderWidth: 1,
    minHeight: 214,
    overflow: 'hidden',
    padding: spacing.md,
  },
  heroCopy: {
    paddingRight: 118,
  },
  heroDescription: {
    color: colors.primaryInk,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    lineHeight: 20,
    marginTop: spacing.sm,
  },
  heroEyebrow: {
    color: colors.primaryDeep,
    fontSize: typography.micro.fontSize,
    fontWeight: '800',
  },
  heroImage: {
    bottom: 50,
    height: 118,
    position: 'absolute',
    right: spacing.sm,
    width: 118,
  },
  heroStats: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  heroTitle: {
    color: colors.primaryDeep,
    fontSize: 24,
    fontWeight: '800',
    lineHeight: 31,
    marginTop: spacing.xs,
  },
  notice: {
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderColor: colors.primarySoftStrong,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  noticeCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  noticeDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
    lineHeight: 17,
  },
  noticeIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 30,
    justifyContent: 'center',
    width: 30,
  },
  noticeTitle: {
    color: colors.primaryDeep,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
  },
  preparationList: {
    gap: spacing.sm,
  },
  prepCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  prepDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
    lineHeight: 18,
  },
  prepHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  prepIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  prepTitle: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '800',
  },
  prepTitleBlock: {
    flex: 1,
    gap: 2,
  },
  prepVerified: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  pressed: {
    opacity: 0.65,
  },
  progressCard: {
    backgroundColor: colors.seaSoftLight,
    borderColor: colors.seaSoft,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md,
  },
  progressCount: {
    color: colors.seaDeep,
    fontSize: 26,
    fontWeight: '800',
  },
  progressDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
    marginTop: 3,
  },
  progressFill: {
    backgroundColor: colors.sea,
    borderRadius: radius.full,
    height: '100%',
  },
  progressHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  progressTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '800',
  },
  progressTrack: {
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    height: 8,
    overflow: 'hidden',
  },
  readingSection: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  readingTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '800',
  },
  ruleCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    ...shadow.sm,
  },
  ruleHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  ruleIcon: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  ruleMeta: {
    alignItems: 'flex-end',
    gap: spacing.xs,
  },
  ruleSubtitle: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
  },
  ruleSummary: {
    color: colors.textStrong,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    lineHeight: 19,
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  ruleTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize + 1,
    fontWeight: '800',
  },
  ruleTitleBlock: {
    flex: 1,
    minWidth: 0,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  sectionDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
    lineHeight: 18,
    marginTop: spacing.xs,
  },
  sectionIntro: {
    paddingHorizontal: spacing.xs,
  },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '800',
  },
  summaryItem: {
    backgroundColor: colors.surface,
    borderColor: colors.primarySoftStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    gap: 2,
    minHeight: 58,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  summaryLabel: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  summaryValue: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '800',
    lineHeight: 17,
  },
  tabBar: {
    backgroundColor: colors.neutralGray,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    padding: spacing.xs,
  },
  tabCount: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: '800',
  },
  tabCountSelected: {
    color: colors.primary,
  },
  tabItem: {
    alignItems: 'center',
    borderRadius: radius.md,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: spacing.xs,
  },
  tabItemSelected: {
    backgroundColor: colors.surface,
    ...shadow.sm,
  },
  tabLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  tabLabelSelected: {
    color: colors.primary,
    fontWeight: '800',
  },
  taskCopy: {
    flex: 1,
    gap: 3,
  },
  taskHint: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: typography.caption.fontWeight,
    lineHeight: 17,
  },
  taskLabel: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
    lineHeight: 20,
  },
  taskLabelChecked: {
    color: colors.textTertiary,
    textDecorationLine: 'line-through',
  },
  taskRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm + 2,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  verifiedLabel: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
});

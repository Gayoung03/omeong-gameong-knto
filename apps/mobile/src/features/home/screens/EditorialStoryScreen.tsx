import Ionicons from '@expo/vector-icons/Ionicons';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import { fetchEditorialStory } from '../api/editorialApi';
import type { EditorialStory } from '../types/home';

type EditorialStoryScreenProps = {
  storyId: string;
};

export function EditorialStoryScreen({ storyId }: EditorialStoryScreenProps) {
  const { data: story, isPending } = useQuery({
    queryKey: ['editorial-story', storyId],
    queryFn: () => fetchEditorialStory(storyId),
    enabled: Boolean(storyId),
  });

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="제주 여행 이야기" />
      {isPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : story ? (
        <StoryArticle story={story} />
      ) : (
        <EmptyState
          description="주소가 잘못되었거나 게시가 종료된 글일 수 있어요."
          icon="document-text-outline"
          title="이야기를 찾을 수 없어요"
        />
      )}
    </SafeAreaView>
  );
}

function StoryArticle({ story }: { story: EditorialStory }) {
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  return (
    <>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.intro}>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{story.category}</Text>
          </View>
          <Text style={styles.title}>{story.title}</Text>
          <Text style={styles.summary}>{story.summary}</Text>
          <View style={styles.metaRow}>
            <Text style={styles.metaText}>{story.author}</Text>
            <View style={styles.metaDot} />
            <Text style={styles.metaText}>{formatPublishedAt(story.publishedAt)}</Text>
            <View style={styles.metaDot} />
            <Text style={styles.metaText}>{story.readingMinutes}분 읽기</Text>
          </View>
        </View>

        <Pressable
          accessibilityLabel="대표 사진 크게 보기"
          accessibilityRole="button"
          onPress={() => setPreviewImageUrl(story.heroImageUrl)}
        >
          <RemoteImage borderRadius={radius.lg} style={styles.heroImage} uri={story.heroImageUrl} />
        </Pressable>

        <View style={styles.articleBody}>
          {story.sections.map((section) => (
            <View key={section.id} style={styles.section}>
              <Text style={styles.sectionTitle}>{section.heading}</Text>
              {section.paragraphs.map((paragraph, index) => (
                <Text key={`${section.id}-${index}`} style={styles.paragraph}>
                  {paragraph}
                </Text>
              ))}
              {section.imageUrl ? (
                <View style={styles.sectionImageBlock}>
                  <Pressable
                    accessibilityLabel={`${section.heading} 사진 크게 보기`}
                    accessibilityRole="button"
                    onPress={() => setPreviewImageUrl(section.imageUrl ?? null)}
                  >
                    <RemoteImage
                      borderRadius={radius.lg}
                      style={styles.sectionImage}
                      uri={section.imageUrl}
                    />
                  </Pressable>
                  {section.imageCaption ? (
                    <Text style={styles.imageCaption}>{section.imageCaption}</Text>
                  ) : null}
                </View>
              ) : null}
            </View>
          ))}

          <View style={styles.tipCard}>
            <View style={styles.tipHeader}>
              <View style={styles.tipIcon}>
                <Ionicons color={colors.primary} name="paw" size={16} />
              </View>
              <Text style={styles.tipTitle}>혼디의 여행 체크</Text>
            </View>
            {story.tips.map((tip) => (
              <View key={tip} style={styles.tipRow}>
                <View style={styles.tipBullet} />
                <Text style={styles.tipText}>{tip}</Text>
              </View>
            ))}
          </View>

          <View style={styles.tagRow}>
            {story.tags.map((tag) => (
              <View key={tag} style={styles.tag}>
                <Text style={styles.tagText}>#{tag}</Text>
              </View>
            ))}
          </View>

          {story.sources.length > 0 ? (
            <View style={styles.sources}>
              <Text style={styles.sourceLabel}>공식 출처</Text>
              {story.sources.map((source) => (
                <Pressable
                  accessibilityLabel={`${source.sourceName} 원문 열기`}
                  accessibilityRole="link"
                  key={source.sourceUrl}
                  onPress={() => void Linking.openURL(source.sourceUrl)}
                  style={({ pressed }) => [styles.sourceLink, pressed && styles.sourceLinkPressed]}
                >
                  <Text style={styles.sourceLinkText}>{source.sourceName} 원문 보기</Text>
                  <Ionicons color={colors.primaryDeep} name="open-outline" size={16} />
                </Pressable>
              ))}
            </View>
          ) : null}
        </View>
      </ScrollView>

      <Modal
        animationType="fade"
        onRequestClose={() => setPreviewImageUrl(null)}
        statusBarTranslucent
        transparent
        visible={Boolean(previewImageUrl)}
      >
        <View accessibilityViewIsModal style={styles.photoViewer}>
          <Pressable
            accessibilityLabel="사진 닫기"
            accessibilityRole="button"
            hitSlop={12}
            onPress={() => setPreviewImageUrl(null)}
            style={styles.photoCloseButton}
          >
            <Ionicons color={colors.surface} name="close" size={30} />
          </Pressable>
          {previewImageUrl ? (
            <Image resizeMode="contain" source={{ uri: previewImageUrl }} style={styles.previewImage} />
          ) : null}
          <Pressable
            accessibilityLabel="사진 닫기"
            onPress={() => setPreviewImageUrl(null)}
            style={styles.photoBackdrop}
          />
        </View>
      </Modal>
    </>
  );
}

function formatPublishedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('ko-KR');
}

const styles = StyleSheet.create({
  articleBody: { gap: spacing.xl },
  centered: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  categoryBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + spacing.xs,
    paddingVertical: spacing.xs + 2,
  },
  categoryText: {
    color: colors.primaryDeep,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  content: { paddingBottom: spacing.xl * 2, paddingHorizontal: spacing.md },
  heroImage: { aspectRatio: 1.45, marginBottom: spacing.xl, width: '100%' },
  imageCaption: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
    marginTop: spacing.sm,
  },
  intro: { paddingBottom: spacing.lg, paddingTop: spacing.lg },
  metaDot: { backgroundColor: colors.textTertiary, borderRadius: 2, height: 3, width: 3 },
  metaRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  metaText: { color: colors.textSecondary, fontSize: typography.caption.fontSize },
  paragraph: { color: colors.textStrong, fontSize: typography.body.fontSize, lineHeight: 27 },
  photoBackdrop: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  photoCloseButton: {
    position: 'absolute',
    right: spacing.md,
    top: spacing.xl,
    zIndex: 2,
  },
  photoViewer: {
    alignItems: 'center',
    backgroundColor: overlayColors.photoViewer,
    flex: 1,
    justifyContent: 'center',
  },
  previewImage: { height: '82%', width: '100%', zIndex: 1 },
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  section: { gap: spacing.sm + spacing.xs },
  sectionImage: { aspectRatio: 1.55, width: '100%' },
  sectionImageBlock: { marginTop: spacing.sm },
  sectionTitle: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '800',
    lineHeight: 26,
  },
  summary: {
    color: colors.textSecondary,
    fontSize: typography.subtitle.fontSize,
    lineHeight: 23,
    marginTop: spacing.sm + spacing.xs,
  },
  sourceLabel: { color: colors.textSecondary, fontSize: typography.caption.fontSize },
  sourceLink: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sourceLinkPressed: { opacity: 0.7 },
  sourceLinkText: { color: colors.primaryDeep, fontSize: typography.label.fontSize, fontWeight: '700' },
  sources: { gap: spacing.sm },
  tag: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + spacing.xs,
    paddingVertical: spacing.sm,
  },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  tagText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  tipBullet: {
    backgroundColor: colors.primary,
    borderRadius: 3,
    height: 5,
    marginTop: 7,
    width: 5,
  },
  tipCard: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoftStrong,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm + spacing.xs,
    padding: spacing.md,
  },
  tipHeader: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  tipIcon: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  tipRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingLeft: spacing.xs,
  },
  tipText: {
    color: colors.textStrong,
    flex: 1,
    fontSize: typography.label.fontSize,
    lineHeight: 20,
  },
  tipTitle: { color: colors.primaryInk, fontSize: typography.subtitle.fontSize, fontWeight: '800' },
  title: {
    color: colors.textPrimary,
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: -0.8,
    lineHeight: 38,
    marginTop: spacing.md,
  },
});

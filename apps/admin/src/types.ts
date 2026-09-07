export type StoryStatus = 'draft' | 'published' | 'archived';
export type StoryKind = 'event' | 'weather' | 'story' | 'guide';

export interface AdminUser {
  id: string;
  email: string | null;
  nickname: string;
  isAdmin: boolean;
}

export interface StoryListItem {
  id: string;
  slug: string;
  kind: StoryKind;
  category: string;
  cardTitle: string;
  title: string;
  status: StoryStatus;
  sourceNames: string[];
  collectedAt: string | null;
  publishedAt: string | null;
  expiresAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StoryListResponse {
  items: StoryListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface EditorialSection {
  id: string;
  heading: string;
  paragraphs: string[];
  imageUrl: string | null;
  imageCaption: string | null;
}

export interface EditorialSource {
  id: string;
  provider: string;
  externalId: string;
  sourceName: string;
  sourceTitle: string;
  sourceUrl: string;
  sourceImageUrl: string | null;
  sourcePublishedAt: string | null;
  collectedAt: string;
}

export interface EditorialAuditLog {
  id: string;
  actorUserId: string;
  action: string;
  previousStatus: string | null;
  nextStatus: string | null;
  changes: Record<string, unknown>;
  createdAt: string;
}

export interface StoryDetail extends Omit<StoryListItem, 'sourceNames' | 'collectedAt'> {
  summary: string;
  heroImageUrl: string;
  sections: EditorialSection[];
  tips: string[];
  tags: string[];
  displayOrder: number;
  generatedByAi: boolean;
  generationModel: string | null;
  sources: EditorialSource[];
  auditLogs: EditorialAuditLog[];
}

export interface StoryUpdatePayload {
  kind: StoryKind;
  category: string;
  cardTitle: string;
  title: string;
  summary: string;
  heroImageUrl: string;
  sections: EditorialSection[];
  tips: string[];
  tags: string[];
  displayOrder: number;
  publishedAt: string | null;
  expiresAt: string | null;
}

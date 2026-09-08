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

/* ------------------------------------------------------------------ */
/* 고객지원 콘솔 — 1:1 문의                                            */
/* ------------------------------------------------------------------ */

export type InquiryStatus = 'pending' | 'completed';
export type InquiryCategory = 'account' | 'pet' | 'saved' | 'schedule' | 'bug' | 'etc';

export const INQUIRY_CATEGORY_LABEL: Record<InquiryCategory, string> = {
  account: '계정 및 회원정보',
  pet: '반려동물 정보',
  saved: '저장한 장소·코스',
  schedule: '여행 일정',
  bug: '오류·불편',
  etc: '기타',
};

export const INQUIRY_STATUS_LABEL: Record<InquiryStatus, string> = {
  pending: '답변 대기',
  completed: '답변 완료',
};

export interface SupportAuditLog {
  id: string;
  actorUserId: string;
  action: string;
  previousStatus: string | null;
  nextStatus: string | null;
  changes: Record<string, unknown>;
  createdAt: string;
}

export interface AdminInquiryListItem {
  id: string;
  category: InquiryCategory;
  status: InquiryStatus;
  title: string;
  askerNickname: string;
  createdAt: string;
  answeredAt: string | null;
}

export interface AdminInquiryListResponse {
  items: AdminInquiryListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface AdminInquiryDetail {
  id: string;
  category: InquiryCategory;
  status: InquiryStatus;
  title: string;
  content: string;
  imageUrls: string[];
  /** 완료된 문의는 관리자가 보낸 전체 답변. */
  answer: string | null;
  answeredAt: string | null;
  /** 답변 편집기 초기값(인사말 + 빈 본문 + 맺음말). 관리자가 자유롭게 수정한다. */
  answerTemplate: string;
  asker: { id: string; nickname: string; email: string | null };
  createdAt: string;
  updatedAt: string;
  auditLogs: SupportAuditLog[];
}

export interface InquiryDraftResponse {
  reply: string;
  usedContext: string[];
  needsHumanReview: boolean;
  model: string;
}

/* ------------------------------------------------------------------ */
/* 고객지원 콘솔 — 공지사항                                            */
/* ------------------------------------------------------------------ */

export type NoticeFilter = 'all' | 'announced' | 'draft';

export interface AdminNoticeListItem {
  id: string;
  title: string;
  isPinned: boolean;
  isActive: boolean;
  publishedAt: string;
  announcedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminNoticeListResponse {
  items: AdminNoticeListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface AdminNoticeDetail extends AdminNoticeListItem {
  content: string;
  auditLogs: SupportAuditLog[];
}

export interface NoticeCreatePayload {
  title: string;
  content: string;
  isPinned: boolean;
  publishedAt: string | null;
}

export interface NoticeUpdatePayload {
  title?: string;
  content?: string;
  isPinned?: boolean;
  isActive?: boolean;
  publishedAt?: string;
}

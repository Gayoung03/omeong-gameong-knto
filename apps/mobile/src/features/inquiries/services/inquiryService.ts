import { toIsoDate } from '@/src/features/travel-logs/utils/dateFormat';
import type { InquiryCategory, InquiryItem } from '@/src/types/inquiry';
import { createId } from '@/src/utils/createId';

import { mockInquiries } from '../mocks/inquiryMocks';

const FETCH_DELAY_MS = 300;
const UPLOAD_DELAY_MS = 400;
const MUTATION_DELAY_MS = 300;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 세션 내 메모리 저장소.
 * TODO: 실제 API 연동 시 이 배열 접근을 apiClient 호출로 교체 (inquiries 테이블)
 */
let currentInquiries: InquiryItem[] = mockInquiries.map((inquiry) => ({ ...inquiry }));

export type InquiryFormInput = {
  category: InquiryCategory;
  title: string;
  content: string;
  /** 앨범에서 고른 로컬 이미지 URI 목록. 최대 3장. */
  localImageUris?: string[];
};

export class InquiryNotFoundError extends Error {
  constructor(inquiryId: string) {
    super(`문의를 찾을 수 없습니다: ${inquiryId}`);
    this.name = 'InquiryNotFoundError';
  }
}

/** 최신 문의가 항상 맨 앞에 온다. TODO: 실제 API 연동 시 GET /inquiries */
export async function fetchInquiries(): Promise<InquiryItem[]> {
  await wait(FETCH_DELAY_MS);
  return [...currentInquiries]
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    .map((inquiry) => ({ ...inquiry }));
}

/** TODO: 실제 API 연동 시 GET /inquiries/{id} */
export async function fetchInquiry(inquiryId: string): Promise<InquiryItem> {
  await wait(FETCH_DELAY_MS);

  const found = currentInquiries.find((inquiry) => inquiry.id === inquiryId);
  if (!found) throw new InquiryNotFoundError(inquiryId);

  return { ...found };
}

/**
 * 목업에서는 로컬 URI를 그대로 돌려준다.
 * TODO: 실제 API 연동 시 이미지 업로드 API 호출 후 서버 URL 반환
 */
export async function uploadInquiryImages(localUris: string[]): Promise<string[]> {
  if (localUris.length === 0) return [];

  await wait(UPLOAD_DELAY_MS);
  return [...localUris];
}

/** TODO: 실제 API 연동 시 POST /inquiries. id·createdAt은 서버가 발급한 값으로 대체된다. */
export async function createInquiry(input: InquiryFormInput): Promise<InquiryItem> {
  await wait(MUTATION_DELAY_MS);

  const created: InquiryItem = {
    id: createId('inquiry'),
    status: 'pending',
    category: input.category,
    title: input.title.trim(),
    content: input.content.trim(),
    createdAt: toIsoDate(new Date()),
    images: input.localImageUris?.length ? [...input.localImageUris] : undefined,
  };

  currentInquiries = [created, ...currentInquiries];
  return { ...created };
}

/** 목업 저장소를 초기 상태로 되돌린다. 검증 스크립트 전용. */
export function __resetInquiriesForTest(): void {
  currentInquiries = mockInquiries.map((inquiry) => ({ ...inquiry }));
}

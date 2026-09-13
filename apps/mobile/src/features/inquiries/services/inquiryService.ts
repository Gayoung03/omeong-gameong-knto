import { isAxiosError } from 'axios';

import { apiClient } from '@/src/services/apiClient';
import { uploadImage } from '@/src/services/uploadImage';
import {
  INQUIRY_CATEGORY_CODE_TO_LABEL,
  INQUIRY_CATEGORY_LABEL_TO_CODE,
  type InquiryCategory,
  type InquiryCategoryCode,
  type InquiryItem,
  type InquiryStatus,
} from '@/src/types/inquiry';

type InquiryListItemResponse = {
  id: string;
  category: InquiryCategoryCode;
  status: InquiryStatus;
  title: string;
  createdAt: string;
  answeredAt: string | null;
};

type InquiryDetailResponse = InquiryListItemResponse & {
  content: string;
  imageUrls: string[];
  answer: string | null;
  updatedAt: string;
};

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

/** API 는 시각(ISO), 화면 타입은 `YYYY-MM-DD` 문자열이라 날짜 부분만 자른다. */
function dateOnly(iso: string | null | undefined): string | undefined {
  return iso ? iso.slice(0, 10) : undefined;
}

function toLabel(code: InquiryCategoryCode): InquiryCategory {
  return INQUIRY_CATEGORY_CODE_TO_LABEL[code] ?? '기타';
}

function toListItem(item: InquiryListItemResponse): InquiryItem {
  return {
    id: item.id,
    status: item.status,
    category: toLabel(item.category),
    title: item.title,
    content: '', // 목록 응답에는 없다 — 상세에서 채워진다
    createdAt: dateOnly(item.createdAt) ?? '',
    answeredAt: dateOnly(item.answeredAt),
  };
}

function toDetail(item: InquiryDetailResponse): InquiryItem {
  return {
    ...toListItem(item),
    content: item.content,
    answer: item.answer ?? undefined,
    images: item.imageUrls?.length ? item.imageUrls : undefined,
  };
}

/** 최신 문의가 항상 맨 앞에 온다(서버 정렬). */
export async function fetchInquiries(): Promise<InquiryItem[]> {
  const { data } = await apiClient.get<{ items: InquiryListItemResponse[] }>('/inquiries', {
    params: { limit: 100 },
  });
  return data.items.map(toListItem);
}

export async function fetchInquiry(inquiryId: string): Promise<InquiryItem> {
  try {
    const { data } = await apiClient.get<InquiryDetailResponse>(`/inquiries/${inquiryId}`);
    return toDetail(data);
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      throw new InquiryNotFoundError(inquiryId);
    }
    throw error;
  }
}

/** 로컬 이미지를 `POST /uploads`(purpose=inquiry)로 올리고 서버 URL 목록을 돌려준다. */
export async function uploadInquiryImages(localUris: string[]): Promise<string[]> {
  if (localUris.length === 0) return [];
  return Promise.all(localUris.map((uri) => uploadImage(uri, 'inquiry')));
}

export async function createInquiry(input: InquiryFormInput): Promise<InquiryItem> {
  const { data } = await apiClient.post<InquiryDetailResponse>('/inquiries', {
    category: INQUIRY_CATEGORY_LABEL_TO_CODE[input.category],
    title: input.title.trim(),
    content: input.content.trim(),
    // useCreateInquiry 가 업로드를 먼저 끝내고 서버 URL 을 넣어 넘긴다.
    imageUrls: input.localImageUris ?? [],
  });
  return toDetail(data);
}

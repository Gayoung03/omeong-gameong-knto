export type InquiryStatus = 'pending' | 'completed';

export type InquiryCategory =
  | '계정 및 회원정보'
  | '반려동물 정보'
  | '저장한 장소·코스'
  | '여행 일정'
  | '오류·불편'
  | '기타';

/** 작성 화면의 유형 선택 시트와 목업이 함께 쓰는 유일한 원본 목록 */
export const INQUIRY_CATEGORY_OPTIONS: InquiryCategory[] = [
  '계정 및 회원정보',
  '반려동물 정보',
  '저장한 장소·코스',
  '여행 일정',
  '오류·불편',
  '기타',
];

export type InquiryItem = {
  id: string;
  status: InquiryStatus;
  category: InquiryCategory;
  title: string;
  content: string;
  /** YYYY-MM-DD */
  createdAt: string;
  /** YYYY-MM-DD. status가 completed일 때만 존재한다. */
  answeredAt?: string;
  answer?: string;
  images?: string[];
};

export const INQUIRY_STATUS_LABEL: Record<InquiryStatus, string> = {
  pending: '답변 대기',
  completed: '답변 완료',
};

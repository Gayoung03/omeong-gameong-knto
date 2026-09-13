export type InquiryStatus = 'pending' | 'completed';

/** API·DB가 쓰는 값(docs/api/notifications.md). 화면 표시는 아래 라벨로 바꾼다. */
export type InquiryCategoryCode = 'account' | 'pet' | 'saved' | 'schedule' | 'bug' | 'etc';

export type InquiryCategory =
  | '계정 및 회원정보'
  | '반려동물 정보'
  | '저장한 장소·코스'
  | '여행 일정'
  | '오류·불편'
  | '기타';

export const INQUIRY_CATEGORY_CODE_TO_LABEL: Record<InquiryCategoryCode, InquiryCategory> = {
  account: '계정 및 회원정보',
  pet: '반려동물 정보',
  saved: '저장한 장소·코스',
  schedule: '여행 일정',
  bug: '오류·불편',
  etc: '기타',
};

export const INQUIRY_CATEGORY_LABEL_TO_CODE = Object.fromEntries(
  Object.entries(INQUIRY_CATEGORY_CODE_TO_LABEL).map(([code, label]) => [label, code]),
) as Record<InquiryCategory, InquiryCategoryCode>;

/** 작성 화면의 유형 선택 시트가 쓰는 원본 목록 */
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

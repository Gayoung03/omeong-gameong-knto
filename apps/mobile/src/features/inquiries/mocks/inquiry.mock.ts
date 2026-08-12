import type { InquiryItem } from '@/src/types/inquiry';

/**
 * 1:1 문의 목업의 유일한 원본.
 * 화면은 이 배열을 직접 import하지 않고 inquiryService를 통해서만 접근한다.
 */
export const mockInquiries: InquiryItem[] = [
  {
    id: 'inquiry-1',
    status: 'pending',
    category: '오류·불편',
    title: '저장한 코스가 목록에 보이지 않아요',
    content: '저장한 코스를 눌렀는데 목록에 표시되지 않습니다.\n앱을 다시 실행해도 그대로예요.',
    createdAt: '2026-08-06',
    images: ['https://placehold.co/400x300'],
  },
  {
    id: 'inquiry-2',
    status: 'completed',
    category: '반려동물 정보',
    title: '고양이도 함께 등록할 수 있나요?',
    content: '강아지 외에 다른 반려동물도 등록할 수 있는지 궁금해요.',
    createdAt: '2026-08-02',
    answeredAt: '2026-08-03',
    answer: '네, 마이페이지의 나의 반려동물에서 고양이도 함께 등록하실 수 있어요.',
  },
  {
    id: 'inquiry-3',
    status: 'completed',
    // 시안의 '여행 로그'는 문의 유형 목록에 없어 기타로 넣는다.
    category: '기타',
    title: '로그 사진 저장이 안돼요',
    content: '여행 로그에서 사진을 저장하려고 하면 아무 반응이 없어요.',
    createdAt: '2026-07-30',
    answeredAt: '2026-07-31',
    answer:
      '확인 결과 저장 데이터 동기화 과정에서 일시적인 오류가 발생했습니다.\n현재는 정상적으로 확인할 수 있도록 조치했습니다.\n다시 확인 부탁드려요.',
  },
  {
    id: 'inquiry-4',
    status: 'pending',
    category: '기타',
    title: '여행 준비 가이드는 어디서 볼 수 있나요?',
    content: '여행 준비 가이드 메뉴를 찾고 있어요.',
    createdAt: '2026-07-28',
  },
];

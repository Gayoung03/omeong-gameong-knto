import type { NoticeItem } from '@/src/types/notice';

/**
 * 공지사항 목업의 유일한 원본.
 * TODO: 실제 API 연동 시 이 배열을 noticeService(GET /notices) 호출로 교체
 */
export const mockNotices: NoticeItem[] = [
  {
    id: 'notice-1',
    title: '오멍가멍 서비스 이용 안내',
    createdAt: '2026.08.06',
    content:
      '안녕하세요. 오멍가멍입니다.\n\n' +
      '오멍가멍은 반려동물과 함께하는 제주 여행을 더욱 편리하고 특별하게 만들어주는 서비스입니다.\n\n' +
      '여행 중 궁금한 점이나 불편한 점이 있다면 마이페이지의 1:1 문의를 이용해 주세요.\n\n' +
      '앞으로도 더 나은 서비스로 보답하겠습니다.\n감사합니다.',
  },
];

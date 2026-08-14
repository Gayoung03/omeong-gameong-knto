export type NoticeItem = {
  id: string;
  title: string;
  content: string;
  /** 화면에 그대로 노출되는 표시용 날짜 (YYYY.MM.DD) */
  createdAt: string;
};

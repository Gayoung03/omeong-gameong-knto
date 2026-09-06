/**
 * 대화 목록 쿼리 키만 따로 둔 파일.
 *
 * **훅 파일에 두면 순환 참조가 된다.** 세션 스토어는 답변이 끝날 때 목록을
 * 무효화해야 하고(제목·미리보기·정렬이 바뀐다), 훅은 삭제에 성공하면 열려 있는
 * 창을 닫으려고 스토어를 부른다. 서로를 import 하게 되므로 둘 다 여기만 본다.
 */

/**
 * `deleted` 를 키에 넣어 목록과 휴지통을 다른 캐시로 둔다.
 *
 * 앞부분(`['chat', 'conversations']`)이 같으므로 그것만 무효화하면 **둘 다**
 * 다시 불러온다 — 지우거나 되살리면 양쪽이 함께 바뀌기 때문에 그게 맞다.
 */
export const conversationsQueryKey = (deleted = false) =>
  ['chat', 'conversations', deleted] as const;

/** 목록·휴지통을 한꺼번에 무효화할 때 쓰는 접두사. */
export const conversationsQueryPrefix = ['chat', 'conversations'] as const;

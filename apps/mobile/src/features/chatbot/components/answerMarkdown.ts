/**
 * 혼디 답변의 서식을 읽어 그릴 것으로 바꾼다. 그리는 쪽은 `AnswerMarkdown.tsx` 다.
 *
 * ## 아는 문법은 넷뿐이다
 *
 * 굵게(`**말**`), 글머리표(`- `), 번호 목록(`1. `), 줄바꿈. 시스템 프롬프트가 모델에게
 * 허용한 것과 **같은 넷**이다(`app/rag/prompts/system.py`).
 *
 * **제목(`###`)은 금지인데도 그려준다.** 처음에는 "프롬프트가 깨진 것이라 여기서 감출
 * 일이 아니다"라고 두었는데, 화면에서 `### 항공사` 가 그대로 찍혔다. 프롬프트로만 막은
 * 규칙은 샌다는 것을 이 저장소는 이미 한 번 배웠다(무게 비교를 파이썬으로 옮긴 일).
 * 모델이 어겨도 **사용자 화면은 깨지지 않아야 한다** — 기호를 떼고 굵은 줄로 그린다.
 * 표·링크는 아직 나온 적이 없어 그대로 둔다.
 *
 * ## 받는 문자열은 늘 잘려 있다
 *
 * 타이핑 효과가 원문을 **글자 하나씩** 잘라 넘긴다(`useChatbot.ts`). 그래서 여는 `**`
 * 만 도착하고 닫는 쪽은 1초 뒤에 오는 상태를 매번 그리게 된다. 평범한 파서는 그때
 * 별표를 글자로 내보냈다가 닫는 기호가 오면 굵게 바꿔서 **깜빡인다.** 규칙 둘로 막는다.
 *
 * 1. **닫히지 않은 `**` 는 끝까지 굵게.** 닫는 기호가 나중에 와도 화면이 그대로다.
 * 2. **맨 끝의 미완성 마커는 그리지 않는다.** 홀로 남은 `*`, 뒤 공백이 아직 안 온
 *    줄머리의 `-` 나 `1.` 이다. 한두 글자라 없어도 티가 안 난다.
 *
 * 자르는 쪽(`useChatbot.ts`)은 건드리지 않는다. 이모지 서로게이트 처리처럼 이미 맞춰
 * 둔 것이 거기 있고, 그리는 쪽이 감당하면 되는 문제다.
 *
 * 파일을 나눈 이유는 **여기만 리액트 없이 실행해 검사할 수 있어서**다. 앱에는 테스트
 * 러너가 없어, 위 두 규칙은 `node` 로 프리픽스를 하나씩 넣어보며 확인했다.
 */

/** 굵기가 같은 글자 덩어리. */
export type Span = { text: string; bold: boolean };

export type Block =
  | { kind: 'paragraph'; spans: Span[] }
  | { kind: 'item'; marker: string; spans: Span[] };

/** `- 항목` · `* 항목`. `**굵게**` 는 별표 뒤가 공백이 아니라 걸리지 않는다. */
const BULLET = /^\s*[-*]\s+(.*)$/;
const ORDERED = /^\s*(\d+)\.\s+(.*)$/;

/** `### 제목`. 프롬프트가 금지했지만 모델이 쓸 때가 있어 받아만 준다. */
const HEADING = /^\s*#{1,6}\s+(.*)$/;

/** 아직 마커가 될지 글자로 남을지 모르는 마지막 줄. */
const PENDING_MARKER = /^\s*(?:[-*]|#{1,6}|\d+\.?)$/;

/** 규칙 2 — 맨 끝의 미완성 마커를 떼어낸다. */
function dropPendingMarker(text: string): string {
  const asterisks = /\*+$/.exec(text);
  // 짝이 맞는 `**` 는 남긴다. 홀수로 끝나면 하나가 아직 오는 중이다.
  const trimmed = asterisks && asterisks[0].length % 2 === 1 ? text.slice(0, -1) : text;

  const lastBreak = trimmed.lastIndexOf('\n');
  const lastLine = trimmed.slice(lastBreak + 1);
  return PENDING_MARKER.test(lastLine) ? trimmed.slice(0, lastBreak + 1) : trimmed;
}

/** 규칙 1 — `**` 를 만날 때마다 굵기를 뒤집는다. 닫히지 않으면 끝까지 굵다. */
function parseSpans(line: string): Span[] {
  const spans: Span[] = [];
  let bold = false;
  let buffer = '';

  for (let index = 0; index < line.length; index += 1) {
    if (line[index] === '*' && line[index + 1] === '*') {
      if (buffer) spans.push({ text: buffer, bold });
      buffer = '';
      bold = !bold;
      index += 1;
      continue;
    }
    buffer += line[index];
  }
  if (buffer) spans.push({ text: buffer, bold });
  return spans;
}

export function parseAnswer(text: string): Block[] {
  const blocks: Block[] = [];

  for (const line of dropPendingMarker(text).split('\n')) {
    // 빈 줄은 문단을 나누는 표시일 뿐이다. 빈 말풍선 줄을 만들지 않는다.
    if (!line.trim()) continue;

    // 제목은 굵은 한 줄로 낮춰 그린다. 기호가 화면에 보이지 않게만 하면 된다.
    const heading = HEADING.exec(line);
    if (heading) {
      const spans = parseSpans(heading[1]).map((span) => ({ ...span, bold: true }));
      blocks.push({ kind: 'paragraph', spans });
      continue;
    }

    const ordered = ORDERED.exec(line);
    if (ordered) {
      blocks.push({ kind: 'item', marker: `${ordered[1]}.`, spans: parseSpans(ordered[2]) });
      continue;
    }

    const bullet = BULLET.exec(line);
    if (bullet) {
      blocks.push({ kind: 'item', marker: '•', spans: parseSpans(bullet[1]) });
      continue;
    }

    blocks.push({ kind: 'paragraph', spans: parseSpans(line) });
  }

  return blocks;
}

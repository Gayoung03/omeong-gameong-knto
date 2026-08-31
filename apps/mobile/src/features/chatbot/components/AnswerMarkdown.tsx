import { type ReactNode, useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '@/src/theme';

import { type Span, parseAnswer } from './answerMarkdown';

/**
 * 혼디 답변을 서식대로 그린다. 무엇을 그릴지 읽어내는 쪽은 `answerMarkdown.ts` 다 —
 * **부분 마크다운을 깜빡임 없이 처리하는 규칙 둘**이 거기 적혀 있다.
 */

type Props = {
  text: string;
  /** 마지막 글자 뒤에 붙일 것. 타이핑 커서가 여기로 들어온다. */
  trailing?: ReactNode;
};

export function AnswerMarkdown({ text, trailing }: Props) {
  const blocks = useMemo(() => parseAnswer(text), [text]);

  const renderSpans = (spans: Span[], tail: ReactNode) => (
    <>
      {spans.map((span, index) => (
        <Text key={index} style={span.bold ? styles.bold : undefined}>
          {span.text}
        </Text>
      ))}
      {tail}
    </>
  );

  return (
    <View>
      {blocks.map((block, index) => {
        // 커서는 **마지막 줄 뒤**에 붙어야 한다. 말풍선 바깥에 두면 목록에서
        // 엉뚱한 줄에 가서 붙는다.
        const tail = index === blocks.length - 1 ? trailing : null;
        const gap = index === 0 ? undefined : styles.gap;

        if (block.kind === 'item') {
          return (
            <View key={index} style={[styles.item, gap]}>
              <Text style={[styles.body, styles.marker]}>{block.marker}</Text>
              <Text style={[styles.body, styles.itemBody]}>
                {renderSpans(block.spans, tail)}
              </Text>
            </View>
          );
        }

        return (
          <Text key={index} style={[styles.body, gap]}>
            {renderSpans(block.spans, tail)}
          </Text>
        );
      })}
      {/* 아직 글자가 한 자도 안 왔을 때도 커서는 보여야 한다. */}
      {blocks.length === 0 && trailing ? <Text style={styles.body}>{trailing}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    color: colors.textPrimary,
    fontSize: 13,
    lineHeight: 19,
  },
  bold: {
    fontWeight: '700',
  },
  gap: {
    marginTop: spacing.xs,
  },
  item: {
    flexDirection: 'row',
  },
  marker: {
    // 마커 폭을 고정해 두 줄로 넘어간 항목이 마커 아래로 흘러들지 않게 한다.
    width: 18,
  },
  itemBody: {
    flex: 1,
  },
});

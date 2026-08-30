import { useCallback, useEffect, useRef } from 'react';

/**
 * 지도 HTML 을 담을 빈 문서. `apps/mobile/public/` 에 있는 실제 파일이라
 * 앱과 같은 출처(배포 시 https://…)로 열린다.
 */
const FRAME_SOURCE = '/kakao-map-frame.html';

type HtmlFrameProps = {
  /** 프레임 안에 그릴 HTML 문서 전체 */
  html: string;
  /** 탭 제목 겸 스크린리더 라벨 */
  title: string;
  backgroundColor: string;
  /** 부모가 iframe 을 직접 다뤄야 할 때 (postMessage·이벤트 출처 확인 등) */
  onFrame?: (frame: HTMLIFrameElement | null) => void;
  /** HTML 을 다 써 넣은 직후 */
  onWrite?: () => void;
};

/**
 * 웹에서 지도 HTML 을 띄우는 iframe. (`react-native-webview` 가 웹을 지원하지 않는다)
 *
 * **`srcDoc` 을 쓰지 않는 이유**
 *
 * srcDoc 문서의 주소는 `about:srcdoc` 이고, 그래서 그 안에서 `location.protocol` 은
 * `https:` 가 아니라 `about:` 이다. 카카오 지도 SDK 로더는 이 값을 보고 실제 지도
 * 스크립트 주소를 만드는데, `https:` 가 아니면 `http://t1.daumcdn.net/...` 을 부른다.
 * HTTPS 로 배포된 페이지에서 이 요청은 혼합 콘텐츠(mixed content)로 차단되고,
 * 지도는 끝내 그려지지 않는다.
 *
 * 로컬 개발 서버는 `http://localhost` 라 차단이 일어나지 않아 이 문제가 보이지 않는다.
 * 배포한 뒤에야 지도만 안 나오는 것으로 드러난다.
 *
 * 그래서 같은 출처의 빈 HTML 파일(`public/kakao-map-frame.html`)을 먼저 띄우고,
 * 그 문서에 지도 HTML 을 써 넣는다. 문서 주소가 `https://…/kakao-map-frame.html` 이
 * 되므로 SDK 도 https 로 지도 스크립트를 불러온다.
 */
export function HtmlFrame({ html, title, backgroundColor, onFrame, onWrite }: HtmlFrameProps) {
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const isFrameReadyRef = useRef(false);
  const writtenHtmlRef = useRef<string | null>(null);

  const writeHtml = useCallback(() => {
    const frame = frameRef.current;
    // 빈 문서가 뜨기 전에는 쓰지 않는다.
    // about:blank 상태에 쓰면 주소가 `about:` 이라 위 문제가 그대로 재현된다.
    if (!frame || !isFrameReadyRef.current) return;

    // 같은 내용을 다시 쓰면 지도가 처음부터 다시 그려진다.
    // document.write 는 load 이벤트를 한 번 더 일으키므로, 이 검사가 무한 반복도 막는다.
    if (writtenHtmlRef.current === html) return;

    const frameDocument = frame.contentDocument;
    if (!frameDocument) return;

    writtenHtmlRef.current = html;
    frameDocument.open();
    frameDocument.write(html);
    frameDocument.close();
    onWrite?.();
  }, [html, onWrite]);

  useEffect(() => {
    writeHtml();
  }, [writeHtml]);

  return (
    <iframe
      aria-label={title}
      onLoad={() => {
        isFrameReadyRef.current = true;
        writeHtml();
      }}
      ref={(frame) => {
        frameRef.current = frame;
        onFrame?.(frame);
      }}
      src={FRAME_SOURCE}
      style={{ width: '100%', height: '100%', border: 0, backgroundColor }}
      title={title}
    />
  );
}

import { JEJU_CENTER, KAKAO_JS_KEY } from '../constants/map';
import type { ScheduleItem } from '../types/trip';

/** WebView 가 앱으로 보내는 메시지 */
export type KakaoMapMessage =
  | { type: 'markerPress'; placeId: string }
  | { type: 'mapPress' }
  | { type: 'ready' }
  | { type: 'error'; message: string };

/** HTML 안에서 쓸 색상. 하드코딩을 피하려고 theme 토큰을 넘겨받는다 */
export type KakaoMapColors = {
  marker: string;
  markerText: string;
  selectedMarker: string;
  routeLine: string;
  background: string;
};

type BuildKakaoMapHtmlParams = {
  items: ScheduleItem[];
  /** 처음부터 강조해둘 장소 */
  initialSelectedPlaceId: string | null;
  colors: KakaoMapColors;
};

/** 문자열을 자바스크립트 리터럴로 안전하게 넣기 위한 처리 */
function toJsonLiteral(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

/**
 * 카카오 지도 JavaScript API 로 Day 별 마커와 경로선을 그리는 HTML 을 만든다.
 *
 * 선택 표시(강조)는 WebView 안에서 스스로 처리하고, 앱에는 어떤 장소가 눌렸는지만 알린다.
 * 앱이 선택 상태를 다시 내려주면 지도를 새로 그려야 해서 화면이 튀기 때문이다.
 * 날짜가 바뀔 때만 HTML 을 새로 만들어 WebView 를 다시 마운트한다.
 */
export function buildKakaoMapHtml({
  items,
  initialSelectedPlaceId,
  colors,
}: BuildKakaoMapHtmlParams): string {
  const markers = items.map((item) => ({
    placeId: item.place.id,
    order: item.order,
    name: item.place.name,
    lat: item.place.latitude,
    lng: item.place.longitude,
  }));

  return `<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
    <style>
      html, body { margin: 0; padding: 0; height: 100%; background: ${colors.background}; }
      #map { width: 100%; height: 100%; }
      .pin {
        align-items: center;
        background: ${colors.marker};
        border: 2px solid ${colors.markerText};
        border-radius: 999px;
        color: ${colors.markerText};
        display: flex;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 13px;
        font-weight: 700;
        height: 28px;
        justify-content: center;
        width: 28px;
      }
      .pin.selected {
        background: ${colors.selectedMarker};
        height: 34px;
        width: 34px;
        font-size: 15px;
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <script>
      var MARKERS = ${toJsonLiteral(markers)};
      var INITIAL_SELECTED_ID = ${toJsonLiteral(initialSelectedPlaceId)};
      var FALLBACK_CENTER = ${toJsonLiteral(JEJU_CENTER)};
      var pinElements = {};

      function highlight(placeId) {
        Object.keys(pinElements).forEach(function (id) {
          pinElements[id].className = id === placeId ? 'pin selected' : 'pin';
        });
      }

      function send(payload) {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify(payload));
        }
      }

      window.onerror = function (message) {
        send({ type: 'error', message: String(message) });
      };

      // 스크립트 태그로 바로 넣지 않고 직접 만들어 붙인다.
      // 이렇게 해야 로드 실패를 onerror 로 잡아서 원인을 구분할 수 있다.
      var sdk = document.createElement('script');
      sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_JS_KEY}&autoload=false';

      sdk.onerror = function () {
        // 왜 실패했는지 알 수 있도록 현재 페이지 출처도 함께 보낸다
        send({
          type: 'error',
          message:
            '스크립트 로드 실패\\n' +
            'origin: ' + String(location.origin) + '\\n' +
            'href: ' + String(location.href) + '\\n' +
            'protocol: ' + String(location.protocol),
        });
      };

      sdk.onload = function () {
        if (typeof kakao === 'undefined' || !kakao.maps) {
          send({ type: 'error', message: '카카오 지도 스크립트가 정상적으로 실행되지 않았어요.' });
          return;
        }

        kakao.maps.load(function () {
          try {
            var container = document.getElementById('map');
            var center = MARKERS.length
              ? new kakao.maps.LatLng(MARKERS[0].lat, MARKERS[0].lng)
              : new kakao.maps.LatLng(FALLBACK_CENTER.latitude, FALLBACK_CENTER.longitude);

            var map = new kakao.maps.Map(container, { center: center, level: 8 });

            kakao.maps.event.addListener(map, 'click', function () {
              highlight(null);
              send({ type: 'mapPress' });
            });

            if (MARKERS.length > 1) {
              new kakao.maps.Polyline({
                map: map,
                path: MARKERS.map(function (marker) {
                  return new kakao.maps.LatLng(marker.lat, marker.lng);
                }),
                strokeWeight: 4,
                strokeColor: ${toJsonLiteral(colors.routeLine)},
                strokeOpacity: 0.85,
                strokeStyle: 'solid',
              });
            }

            MARKERS.forEach(function (marker) {
              var element = document.createElement('div');
              element.className = 'pin';
              element.textContent = String(marker.order);
              element.addEventListener('click', function (event) {
                event.stopPropagation();
                highlight(marker.placeId);
                send({ type: 'markerPress', placeId: marker.placeId });
              });
              pinElements[marker.placeId] = element;

              if (marker.placeId === INITIAL_SELECTED_ID) {
                element.className = 'pin selected';
              }

              new kakao.maps.CustomOverlay({
                map: map,
                position: new kakao.maps.LatLng(marker.lat, marker.lng),
                content: element,
                yAnchor: 0.5,
              });
            });

            if (MARKERS.length > 1) {
              var bounds = new kakao.maps.LatLngBounds();
              MARKERS.forEach(function (marker) {
                bounds.extend(new kakao.maps.LatLng(marker.lat, marker.lng));
              });
              map.setBounds(bounds, 60, 60, 60, 60);
            }

            send({ type: 'ready' });
          } catch (error) {
            send({ type: 'error', message: String(error) });
          }
        });
      };

      document.head.appendChild(sdk);
    </script>
  </body>
</html>`;
}

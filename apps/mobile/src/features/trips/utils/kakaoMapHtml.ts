import { JEJU_CENTER, KAKAO_JS_KEY } from '../constants/map';
import type { PlaceCandidate, PlaceCategory, ScheduleItem } from '../types/trip';

/** WebView 가 앱으로 보내는 메시지 */
export type KakaoMapMessage =
  | { type: 'markerPress'; placeId: string }
  | { type: 'mapPress' }
  | { type: 'ready' }
  | { type: 'error'; message: string };

/** 지도를 어느 범위에 맞출지 (앱에서 injectJavaScript 로 호출) */
export type KakaoMapFitMode = 'route' | 'candidates' | 'all';

/** HTML 안에서 쓸 색상. 하드코딩을 피하려고 theme 토큰을 넘겨받는다 */
export type KakaoMapColors = {
  marker: string;
  markerText: string;
  selectedMarker: string;
  routeLine: string;
  background: string;
  /** 아직 일정에 담기지 않은 후보 장소 마커 */
  candidateMarker: string;
};

type BuildKakaoMapHtmlParams = {
  items: ScheduleItem[];
  /** 처음부터 강조해둘 장소 */
  initialSelectedPlaceId: string | null;
  colors: KakaoMapColors;
  /**
   * 일정에 담기 전 후보 장소.
   * 순번 대신 카테고리 아이콘으로 표시하고, 경로선에는 포함하지 않는다.
   */
  candidates?: PlaceCandidate[];
  /** 지도를 처음 그릴 때 맞출 범위 */
  initialFitMode?: KakaoMapFitMode;
};

const CATEGORY_ICONS: Record<PlaceCategory, string> = {
  attraction: '🚩',
  restaurant: '🍴',
  cafe: '☕',
  accommodation: '🏨',
  etc: '📍',
};

/** 문자열을 자바스크립트 리터럴로 안전하게 넣기 위한 처리 */
function toJsonLiteral(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

/**
 * 카카오 지도 JavaScript API 로 마커와 경로선을 그리는 HTML 을 만든다.
 *
 * 선택 표시(강조)는 WebView 안에서 스스로 처리하고, 앱에는 어떤 장소가 눌렸는지만 알린다.
 * 앱이 선택 상태를 다시 내려주면 지도를 새로 그려야 해서 화면이 튀기 때문이다.
 * 지도를 다시 그리는 시점은 TripMapView 의 redrawKey 로 정한다.
 *
 * 범위 이동은 `window.fitTo('route' | 'candidates' | 'all')` 을 앱에서 호출해 처리한다.
 * 이것도 같은 이유로 HTML 을 새로 만들지 않고 안에서 처리한다.
 */
export function buildKakaoMapHtml({
  items,
  initialSelectedPlaceId,
  colors,
  candidates = [],
  initialFitMode = 'route',
}: BuildKakaoMapHtmlParams): string {
  const encodedKakaoKey = encodeURIComponent(KAKAO_JS_KEY);
  const markers = items.map((item) => ({
    placeId: item.place.id,
    order: item.order,
    name: item.place.name,
    lat: item.place.latitude,
    lng: item.place.longitude,
  }));

  // 이미 일정에 담긴 장소는 순번 마커로 이미 그려져 있으므로 후보에서 뺀다
  const scheduledPlaceIds = new Set(items.map((item) => item.place.id));
  const candidateMarkers = candidates
    .filter((candidate) => !scheduledPlaceIds.has(candidate.id))
    .map((candidate) => ({
      placeId: candidate.id,
      icon: CATEGORY_ICONS[candidate.category],
      name: candidate.name,
      lat: candidate.latitude,
      lng: candidate.longitude,
    }));

  return `<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
    <meta name="referrer" content="no-referrer" />
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
      .candidate {
        align-items: center;
        background: ${colors.markerText};
        border: 2px solid ${colors.candidateMarker};
        border-radius: 999px;
        display: flex;
        font-size: 14px;
        height: 30px;
        justify-content: center;
        width: 30px;
      }
      .candidate.selected {
        background: ${colors.candidateMarker};
        border-color: ${colors.markerText};
        font-size: 17px;
        height: 38px;
        width: 38px;
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <script>
      var MARKERS = ${toJsonLiteral(markers)};
      var CANDIDATES = ${toJsonLiteral(candidateMarkers)};
      var INITIAL_SELECTED_ID = ${toJsonLiteral(initialSelectedPlaceId)};
      var INITIAL_FIT_MODE = ${toJsonLiteral(initialFitMode)};
      var FALLBACK_CENTER = ${toJsonLiteral(JEJU_CENTER)};
      var pinElements = {};
      var pinBaseClasses = {};

      function highlight(placeId) {
        Object.keys(pinElements).forEach(function (id) {
          var baseClass = pinBaseClasses[id];
          pinElements[id].className = id === placeId ? baseClass + ' selected' : baseClass;
        });
      }

      function send(payload) {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify(payload));
        } else if (window.parent !== window) {
          window.parent.postMessage(JSON.stringify(payload), '*');
        }
      }

      window.addEventListener('message', function (event) {
        var message = event.data;
        if (message && message.type === 'fitTo' && window.fitTo) {
          window.fitTo(message.mode);
        }
      });

      window.onerror = function (message) {
        send({ type: 'error', message: String(message) });
      };

      // 스크립트 태그로 바로 넣지 않고 직접 만들어 붙인다.
      // 이렇게 해야 로드 실패를 onerror 로 잡아서 원인을 구분할 수 있다.
      var sdk = document.createElement('script');
      sdk.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodedKakaoKey}&autoload=false';

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
            var firstPoint = MARKERS[0] || CANDIDATES[0];
            var center = firstPoint
              ? new kakao.maps.LatLng(firstPoint.lat, firstPoint.lng)
              : new kakao.maps.LatLng(FALLBACK_CENTER.latitude, FALLBACK_CENTER.longitude);

            var map = new kakao.maps.Map(container, { center: center, level: 8 });

            kakao.maps.event.addListener(map, 'click', function () {
              highlight(null);
              send({ type: 'mapPress' });
            });

            function addPin(marker, baseClass, content) {
              var element = document.createElement('div');
              element.className = baseClass;
              element.textContent = content;
              element.addEventListener('click', function (event) {
                event.stopPropagation();
                highlight(marker.placeId);
                send({ type: 'markerPress', placeId: marker.placeId });
              });

              pinElements[marker.placeId] = element;
              pinBaseClasses[marker.placeId] = baseClass;

              if (marker.placeId === INITIAL_SELECTED_ID) {
                element.className = baseClass + ' selected';
              }

              new kakao.maps.CustomOverlay({
                map: map,
                position: new kakao.maps.LatLng(marker.lat, marker.lng),
                content: element,
                yAnchor: 0.5,
              });
            }

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

            CANDIDATES.forEach(function (marker) {
              addPin(marker, 'candidate', marker.icon);
            });

            MARKERS.forEach(function (marker) {
              addPin(marker, 'pin', String(marker.order));
            });

            // 앱에서 지도 범위를 바꿀 때 쓴다. HTML 을 새로 만들지 않기 위한 통로다
            window.fitTo = function (mode) {
              var points =
                mode === 'route'
                  ? MARKERS
                  : mode === 'candidates'
                    ? CANDIDATES
                    : MARKERS.concat(CANDIDATES);

              if (points.length === 0) {
                map.setLevel(9);
                map.setCenter(
                  new kakao.maps.LatLng(FALLBACK_CENTER.latitude, FALLBACK_CENTER.longitude),
                );
                return;
              }

              if (points.length === 1) {
                map.setLevel(5);
                map.setCenter(new kakao.maps.LatLng(points[0].lat, points[0].lng));
                return;
              }

              var bounds = new kakao.maps.LatLngBounds();
              points.forEach(function (point) {
                bounds.extend(new kakao.maps.LatLng(point.lat, point.lng));
              });
              map.setBounds(bounds, 60, 60, 60, 60);
            };

            window.fitTo(INITIAL_FIT_MODE);
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

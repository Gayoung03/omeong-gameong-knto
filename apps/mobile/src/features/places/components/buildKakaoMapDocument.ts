import { colors } from '@/src/theme';

import type { KakaoMapPlace } from './KakaoPlaceMap.types';

function serializeForInlineScript(value: unknown) {
  return JSON.stringify(value).replaceAll('<', '\\u003c');
}

/**
 * WebView 안의 HTML 은 theme 토큰을 직접 참조할 수 없다.
 * 그래서 필요한 색만 이 객체로 추려서 문자열에 끼워 넣는다.
 * (개발 가이드 9항 — `trips/utils/kakaoMapHtml.ts` 와 같은 방식)
 */
const mapColors = {
  canvas: colors.seaSoftLight,
  statusText: colors.textSecondary,
  placeName: colors.basalt,
  placeAddress: colors.textSecondary,
  categoryText: colors.seaDeep,
  categoryBg: colors.seaSoft,
} as const;

export function buildKakaoMapDocument(appKey: string, places: KakaoMapPlace[]) {
  const encodedAppKey = encodeURIComponent(appKey);
  const serializedPlaces = serializeForInlineScript(places);

  return `<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no" />
    <!--
      카카오 지도 SDK 를 부를 때 출처(Referer)를 보내지 않는다.
      웹에서는 이 문서가 iframe(srcdoc)으로 뜨면서 부모 주소(localhost:8081)를 출처로 물고 가는데,
      카카오 콘솔은 localhost 를 사이트 도메인으로 받아주지 않아 SDK 로드가 거부된다.
      배포 도메인을 콘솔에 등록한 뒤에는 이 meta 를 지워도 된다.
    -->
    <meta name="referrer" content="no-referrer" />
    <style>
      html, body, #map { width: 100%; height: 100%; margin: 0; overflow: hidden; }
      body { background: ${mapColors.canvas}; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }
      #status {
        position: absolute;
        inset: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        color: ${mapColors.statusText};
        font-size: 14px;
        text-align: center;
        background: ${mapColors.canvas};
      }
      .place-info { min-width: 160px; padding: 10px 12px; line-height: 1.35; }
      .place-name { color: ${mapColors.placeName}; font-size: 14px; font-weight: 800; }
      .place-address { margin-top: 4px; color: ${mapColors.placeAddress}; font-size: 11px; }
      .place-category {
        display: inline-block;
        margin-top: 7px;
        padding: 3px 7px;
        border-radius: 6px;
        color: ${mapColors.categoryText};
        font-size: 10px;
        font-weight: 700;
        background: ${mapColors.categoryBg};
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <div id="status">카카오 지도를 불러오는 중이에요</div>
    <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodedAppKey}&autoload=false"></script>
    <script>
      const places = ${serializedPlaces};
      const status = document.getElementById('status');

      function showError(message) {
        status.textContent = message;
        status.style.display = 'flex';
      }

      function createInfoContent(place) {
        const root = document.createElement('div');
        root.className = 'place-info';

        const name = document.createElement('div');
        name.className = 'place-name';
        name.textContent = place.name;

        const address = document.createElement('div');
        address.className = 'place-address';
        address.textContent = place.address;

        const category = document.createElement('span');
        category.className = 'place-category';
        category.textContent = place.category;

        root.append(name, address, category);
        return root;
      }

      function initializeMap() {
        if (!window.kakao || !window.kakao.maps) {
          showError('카카오 지도 설정을 확인해 주세요.');
          return;
        }

        window.kakao.maps.load(function () {
          const center = new window.kakao.maps.LatLng(33.3786, 126.5580);
          const map = new window.kakao.maps.Map(document.getElementById('map'), {
            center,
            level: 9,
          });
          const zoomControl = new window.kakao.maps.ZoomControl();
          map.addControl(zoomControl, window.kakao.maps.ControlPosition.RIGHT);

          if (places.length === 0) {
            status.textContent = '조건에 맞는 장소가 없어요.';
            return;
          }

          const bounds = new window.kakao.maps.LatLngBounds();
          let openInfoWindow = null;

          places.forEach(function (place) {
            const position = new window.kakao.maps.LatLng(place.latitude, place.longitude);
            const marker = new window.kakao.maps.Marker({ map, position, title: place.name });
            const infoWindow = new window.kakao.maps.InfoWindow({
              content: createInfoContent(place),
              removable: true,
            });

            window.kakao.maps.event.addListener(marker, 'click', function () {
              if (openInfoWindow) openInfoWindow.close();
              infoWindow.open(map, marker);
              openInfoWindow = infoWindow;
            });

            bounds.extend(position);
          });

          map.setBounds(bounds, 56, 56, 56, 56);
          status.style.display = 'none';
        });
      }

      window.addEventListener('error', function () {
        showError('지도를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.');
      });

      initializeMap();
    </script>
  </body>
</html>`;
}

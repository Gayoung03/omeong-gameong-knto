import { useRouter, type Href } from 'expo-router';
import { useCallback } from 'react';

/**
 * 뒤로 가되, 갈 곳이 없으면 정해둔 화면으로 보낸다.
 *
 * `router.back()` 만 부르면 **웹에서 죽는다.** 주소로 바로 들어오거나 새로고침한
 * 뒤에는 히스토리가 비어 있어서 `GO_BACK was not handled by any navigator` 가 뜨고,
 * 사용자는 화면에 갇힌다. 앱에서는 대개 히스토리가 있어 드러나지 않는다.
 *
 * 이 앱은 앱 스토어 승인이 늦어질 경우 **웹으로 심사**를 받을 수 있어,
 * 웹에서만 갇히는 화면을 남겨둘 수 없다.
 *
 * `fallback` 은 "이 화면을 닫으면 논리적으로 어디로 가야 하는가"로 정한다.
 * 대개 그 화면이 속한 목록이나 탭이다.
 */
export function useSafeBack(fallback: Href) {
  const router = useRouter();

  return useCallback(() => {
    if (router.canGoBack()) {
      router.back();
      return;
    }

    router.replace(fallback);
  }, [fallback, router]);
}

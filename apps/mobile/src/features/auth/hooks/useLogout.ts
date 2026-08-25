import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';

import { signOut } from '../services/authStorage';

/**
 * 로그아웃 확인 모달의 열림 상태와 확정 처리를 한곳에 모은다.
 * 마이페이지 하단 링크와 설정 화면이 같은 흐름을 공유해야 하므로 훅으로 뺐다.
 *
 * 저장된 세션을 지우고 로그인 화면으로 보낸다.
 * 세션은 `(tabs)/_layout` 이 진입할 때마다 확인하므로, 지운 뒤에는 탭으로 되돌아갈 수 없다.
 */
export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isConfirmVisible, setConfirmVisible] = useState(false);
  const [isLoggingOut, setLoggingOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();

  const requestLogout = () => {
    setErrorMessage(undefined);
    setConfirmVisible(true);
  };
  const cancelLogout = () => setConfirmVisible(false);

  const confirmLogout = () => {
    if (isLoggingOut) return;
    setLoggingOut(true);
    setConfirmVisible(false);

    void signOut()
      .then(() => {
        // 다음 사용자가 이전 사용자의 캐시된 데이터를 잠깐 보게 되는 것을 막는다.
        queryClient.clear();
        router.replace('/login');
      })
      .catch((error: unknown) => {
        // 세션을 못 지운 채 로그인 화면으로 보내면 뒤로 가기로 다시 들어올 수 있다.
        // 실패하면 이동하지 않고 원인을 화면에 남긴다.
        //
        // `Alert` 을 쓰지 않는다 — 웹에서는 뜨지 않아 눌러도 아무 일이 없는 것처럼 보인다.
        const detail = error instanceof Error ? error.message : String(error);
        setErrorMessage(
          __DEV__
            ? `로그아웃하지 못했어요 (${detail})`
            : '로그아웃하지 못했어요. 잠시 후 다시 시도해 주세요.',
        );
      })
      .finally(() => {
        setLoggingOut(false);
      });
  };

  return {
    isConfirmVisible,
    isLoggingOut,
    errorMessage,
    requestLogout,
    cancelLogout,
    confirmLogout,
  };
}

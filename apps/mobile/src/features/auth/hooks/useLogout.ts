import { useState } from 'react';

/**
 * 로그아웃 확인 모달의 열림 상태와 확정 처리를 한곳에 모은다.
 * 마이페이지 하단 링크와 설정 화면이 같은 흐름을 공유해야 하므로 훅으로 뺐다.
 */
export function useLogout() {
  const [isConfirmVisible, setConfirmVisible] = useState(false);

  const requestLogout = () => setConfirmVisible(true);
  const cancelLogout = () => setConfirmVisible(false);

  const confirmLogout = () => {
    setConfirmVisible(false);
    // TODO: 실제 로그아웃 처리(토큰 삭제 + 로그인 화면 이동) 연결
  };

  return { isConfirmVisible, requestLogout, cancelLogout, confirmLogout };
}

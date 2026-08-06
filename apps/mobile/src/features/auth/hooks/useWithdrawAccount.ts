import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';

import {
  clearLocalUserData,
  shouldClearAppCacheOnWithdraw,
  withdrawAccount,
} from '../services/accountService';

/**
 * 탈퇴 요청부터 로컬 정리·화면 이동까지의 흐름을 한곳에 모은다.
 * 화면은 이 훅만 호출하고 저장소나 라우팅을 직접 다루지 않는다.
 */
export function useWithdrawAccount() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();

  const withdraw = async () => {
    // 중복 클릭으로 요청이 두 번 나가지 않게 막는다.
    if (isPending) return;

    setIsPending(true);
    setErrorMessage(undefined);

    try {
      await withdrawAccount();
      await clearLocalUserData();
      if (shouldClearAppCacheOnWithdraw()) queryClient.clear();

      // 뒤로가기로 탈퇴 전 화면에 돌아가지 못하도록 쌓인 화면을 모두 정리한다.
      if (router.canDismiss()) router.dismissAll();
      router.replace('/login');
    } catch {
      setErrorMessage('탈퇴 처리에 실패했어요. 잠시 후 다시 시도해 주세요.');
    } finally {
      setIsPending(false);
    }
  };

  return { withdraw, isPending, errorMessage };
}

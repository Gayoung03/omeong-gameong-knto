import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  readTravelLogGuideState,
  writeTravelLogGuideState,
} from '../services/travelLogGuideStorage';

const GUIDE_QUERY_KEY = ['travel-log-guide'] as const;

/**
 * 여행 기록 사용법 안내를 언제 띄울지 정한다.
 *
 * **`useEffect` 안에서 `setState` 를 하지 않는다.** 이 저장소에서 금지된 패턴이고
 * (`react-hooks/set-state-in-effect`), 저장값을 읽어오는 것은 비동기라 그쪽으로
 * 짜기 쉽다. 대신 TanStack Query 로 읽고 **띄울지 말지는 계산으로 낸다.**
 *
 * **띄울지 말지는 체크박스 하나가 정한다.** 체크하지 않고 닫으면 다음에 또 뜨고,
 * "다시 보지 않기" 를 체크해야 그만 뜬다.
 *
 * 처음엔 "본 적 있으면 그만" 으로 짰다가 되돌렸다 — 체크박스를 두고서 **체크하지
 * 않아도 다시 안 뜨면 그 체크박스는 아무 일도 하지 않는 것**이고, 사용자는 "체크
 * 안 했으니 또 나오겠네" 로 읽는다. 화면이 약속한 대로 동작해야 한다.
 *
 * 성가심은 사용자가 스스로 끈다. 그래서 체크박스가 있는 것이다.
 */
export function useTravelLogGuide() {
  const queryClient = useQueryClient();
  const { data: state } = useQuery({
    queryKey: GUIDE_QUERY_KEY,
    queryFn: readTravelLogGuideState,
    // 기기에 있는 값이라 화면을 다시 볼 때마다 읽을 이유가 없다.
    staleTime: Infinity,
  });

  /** 사용자가 이번 화면에서 닫았다. 저장이 끝나기 전에 창이 남아 있지 않게 한다. */
  const [closed, setClosed] = useState(false);
  /** 도움말 버튼으로 연 경우. 숨김 설정과 무관하게 띄운다. */
  const [opened, setOpened] = useState(false);

  // `seen` 은 보지 않는다 — 껐는지(`hidden`)만 본다.
  const shouldAutoShow = state != null && !state.hidden;
  const visible = opened || (!closed && shouldAutoShow);

  const open = () => {
    setClosed(false);
    setOpened(true);
  };

  const close = (dontShowAgain: boolean) => {
    setOpened(false);
    setClosed(true);

    // `seen` 은 "언젠가 한 번 봤다" 는 기록으로만 남긴다(지금은 쓰지 않는다).
    const next = { seen: true, hidden: dontShowAgain || state?.hidden === true };
    queryClient.setQueryData(GUIDE_QUERY_KEY, next);
    void writeTravelLogGuideState(next);
  };

  return { visible, open, close };
}

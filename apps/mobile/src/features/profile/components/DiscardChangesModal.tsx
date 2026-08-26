import { ConfirmModal } from '@/src/components/feedback/ConfirmModal';

type Props = {
  onDiscard: () => void;
  onContinue: () => void;
  visible: boolean;
  description?: string;
};

/**
 * "저장 안 하고 나갈까요?" 확인 창.
 *
 * 화면 다섯 곳이 같은 문구로 쓰고 있어서 이름을 남겨뒀다.
 * 실제 그리기는 공용 `ConfirmModal` 이 한다 — 같은 생김새의 모달을
 * 네 벌 따로 들고 있던 것을 하나로 합쳤다.
 */
export function DiscardChangesModal({
  onDiscard,
  onContinue,
  visible,
  description = '프로필 정보의 변경 사항이 저장되지 않아요.',
}: Props) {
  return (
    <ConfirmModal
      cancelLabel="계속 수정"
      confirmLabel="나가기"
      description={description}
      onCancel={onContinue}
      onConfirm={onDiscard}
      title="변경사항을 저장하지 않고 나갈까요?"
      tone="destructive"
      visible={visible}
    />
  );
}

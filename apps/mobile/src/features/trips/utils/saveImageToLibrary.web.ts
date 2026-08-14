/**
 * 웹에는 사진첩 개념이 없고 expo-media-library 도 웹을 지원하지 않는다.
 * 화면에서 저장 버튼을 감추거나 안내를 띄우는 판단에 쓴다.
 *
 * 타입을 native 구현에서 import 하면 웹에서는 자기 자신을 가리켜 순환이 되므로
 * 같은 모양의 타입을 여기서 따로 선언한다.
 */
export const IS_SAVE_IMAGE_SUPPORTED = false;

export type SaveImageResult = 'saved' | 'permission-denied';

export async function saveImageToLibrary(): Promise<SaveImageResult> {
  throw new Error('웹에서는 사진첩 저장을 지원하지 않습니다.');
}

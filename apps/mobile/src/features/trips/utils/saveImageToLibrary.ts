import * as MediaLibrary from 'expo-media-library';

/**
 * 이 플랫폼에서 사진첩 저장을 지원하는지 여부.
 * 웹에서는 saveImageToLibrary.web.ts 가 대신 쓰이며 false 가 된다.
 */
export const IS_SAVE_IMAGE_SUPPORTED = true;

export type SaveImageResult = 'saved' | 'permission-denied';

/**
 * 캡처한 이미지를 사진첩에 저장한다.
 *
 * expo-media-library 는 웹 구현이 없어(`next` 네이티브 모듈 미지원) 최상위에서 import 하면
 * 웹 번들이 깨진다. 그래서 이 파일로 분리하고 `.web.ts` 대체 구현을 둔다.
 */
export async function saveImageToLibrary(uri: string): Promise<SaveImageResult> {
  // 저장만 하면 되므로 쓰기 전용 권한만 요청한다.
  // 전체 접근 권한을 요구하면 '선택된 사진만 허용' 을 고른 사용자에게서 실패한다.
  const permission = await MediaLibrary.requestPermissionsAsync(true);

  if (!permission.granted) {
    return 'permission-denied';
  }

  // SDK 57 에서 saveToLibraryAsync·createAssetAsync 는 폐기됐다.
  // 앨범을 지정하지 않으면 기본 사진첩에 저장된다.
  await MediaLibrary.Asset.create(uri);

  return 'saved';
}

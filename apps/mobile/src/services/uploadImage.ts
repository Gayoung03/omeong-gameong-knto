import { Platform } from 'react-native';

import { apiClient } from './apiClient';

export type UploadPurpose =
  | 'review'
  | 'travel_log'
  | 'inquiry'
  | 'profile'
  | 'pet'
  | 'place';

type UploadResponse = {
  fileUrl: string;
  contentType: string;
  sizeBytes: number;
};

function filePart(localUri: string) {
  const path = localUri.split('?')[0];
  const name = path.split('/').pop() || 'image.jpg';
  const extension = name.split('.').pop()?.toLowerCase();
  const type = extension === 'png'
    ? 'image/png'
    : extension === 'webp'
      ? 'image/webp'
      : 'image/jpeg';

  return { uri: localUri, name, type } as unknown as Blob;
}

/** 로컬 이미지 한 장을 저장하고 DB에 넣을 CloudFront URL만 반환한다. */
export async function uploadImage(localUri: string, purpose: UploadPurpose): Promise<string> {
  const body = new FormData();
  if (Platform.OS === 'web') {
    const file = await (await fetch(localUri)).blob();
    body.append('file', file, 'image');
  } else {
    body.append('file', filePart(localUri));
  }
  body.append('purpose', purpose);

  const response = await apiClient.post<UploadResponse>('/uploads', body, {
    timeout: 30_000,
  });
  return response.data.fileUrl;
}

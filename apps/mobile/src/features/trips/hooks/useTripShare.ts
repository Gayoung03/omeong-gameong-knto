import * as Clipboard from 'expo-clipboard';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import { useCallback, useState } from 'react';
import { Alert, Share, type View } from 'react-native';
import { captureRef } from 'react-native-view-shot';

import { buildTripShareUrl } from '../constants/share';
import type { Trip } from '../types/trip';

/**
 * 사용자에게 보여줄 오류 설명.
 * 개발 중에는 원인을 바로 알 수 있도록 실제 메시지를 노출하고,
 * 배포 빌드에서는 안내 문구만 보여준다.
 */
function describeError(error: unknown): string {
  if (__DEV__ && error instanceof Error) {
    return error.message;
  }
  return '잠시 후 다시 시도해주세요.';
}

type UseTripShareParams = {
  /** 여행을 아직 불러오는 중일 수 있어 비어있는 값을 허용한다 */
  trip: Pick<Trip, 'id' | 'title'> | null | undefined;
};

/**
 * 여행 공유(링크 복사·OS 공유)와 일정 이미지 저장을 담당한다.
 * TODO: 실제 공유 페이지가 생기면 constants/share.ts 의 주소를 교체한다.
 */
export function useTripShare({ trip }: UseTripShareParams) {
  const [isSaving, setIsSaving] = useState(false);

  const shareUrl = trip ? buildTripShareUrl(trip.id) : '';

  const copyLink = useCallback(async () => {
    if (!shareUrl) {
      return;
    }
    await Clipboard.setStringAsync(shareUrl);
    Alert.alert('링크를 복사했어요', shareUrl);
  }, [shareUrl]);

  /**
   * 링크를 OS 기본 공유 시트로 보낸다.
   *
   * iOS 는 `url` 을 함께 넘기면 그쪽을 우선 처리하면서 시트가 뜨지 않는 경우가 있어,
   * 주소를 `message` 안에 넣고 `url` 은 넘기지 않는다.
   * expo-sharing 은 파일 전용이라 링크 공유에는 쓰지 않는다.
   *
   * TODO: 동작 미확인. iOS 시뮬레이터 + Expo Go 환경에서는 공유 시트가 뜨지 않고
   *       오류도 나지 않는다 (시뮬레이터에 공유 대상 앱이 없어서로 추정).
   *       실기기나 개발 빌드에서 한 번 확인이 필요하다.
   */
  const shareLink = useCallback(async () => {
    if (!trip || !shareUrl) {
      return;
    }

    try {
      await Share.share({
        message: `${trip.title} 여행 일정 보러가기\n${shareUrl}`,
      });
    } catch (error) {
      Alert.alert('공유하지 못했어요', describeError(error));
    }
  }, [shareUrl, trip]);

  /** 캡처한 이미지를 사진첩에 저장한다 */
  const saveImage = useCallback(async (viewRef: React.RefObject<View | null>) => {
    if (!viewRef.current) {
      Alert.alert('저장하지 못했어요', '잠시 후 다시 시도해주세요.');
      return;
    }

    setIsSaving(true);

    try {
      // 저장만 하면 되므로 쓰기 전용 권한만 요청한다.
      // 전체 접근 권한을 요구하면 '선택된 사진만 허용' 을 고른 사용자에게서 실패한다.
      const permission = await MediaLibrary.requestPermissionsAsync(true);

      if (!permission.granted) {
        Alert.alert(
          '사진 접근 권한이 필요해요',
          '설정에서 사진 저장을 허용하면 일정을 이미지로 남길 수 있어요.',
        );
        return;
      }

      const uri = await captureRef(viewRef, { format: 'png', quality: 1, result: 'tmpfile' });

      // SDK 57 에서 saveToLibraryAsync·createAssetAsync 는 폐기됐다.
      // 앨범을 지정하지 않으면 기본 사진첩에 저장된다.
      await MediaLibrary.Asset.create(uri);

      Alert.alert('사진첩에 저장했어요');
    } catch (error) {
      Alert.alert('저장하지 못했어요', describeError(error));
    } finally {
      setIsSaving(false);
    }
  }, []);

  /** 캡처한 이미지를 다른 앱으로 바로 공유한다 */
  const shareImage = useCallback(async (viewRef: React.RefObject<View | null>) => {
    if (!viewRef.current) {
      return;
    }

    const canShare = await Sharing.isAvailableAsync();

    if (!canShare) {
      Alert.alert('공유를 지원하지 않는 기기예요');
      return;
    }

    setIsSaving(true);

    try {
      const uri = await captureRef(viewRef, { format: 'png', quality: 1, result: 'tmpfile' });
      await Sharing.shareAsync(uri, { mimeType: 'image/png', UTI: 'public.png' });
    } catch (error) {
      Alert.alert('공유하지 못했어요', describeError(error));
    } finally {
      setIsSaving(false);
    }
  }, []);

  return { shareUrl, isSaving, copyLink, shareLink, saveImage, shareImage };
}

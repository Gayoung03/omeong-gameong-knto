import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { InquiryItem } from '@/src/types/inquiry';

import { inquiriesQueryKey, inquiryQueryKey } from './useInquiries';
import {
  createInquiry,
  uploadInquiryImages,
  type InquiryFormInput,
} from '../services/inquiryService';

export function useCreateInquiry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: InquiryFormInput): Promise<InquiryItem> => {
      // 업로드가 실패하면 등록 자체를 진행하지 않아 사용자가 그대로 재시도할 수 있다.
      const uploadedUrls = await uploadInquiryImages(input.localImageUris ?? []);

      return createInquiry({ ...input, localImageUris: uploadedUrls });
    },
    onSuccess: (created) => {
      // 목록은 최신순이라 새 문의가 항상 맨 앞에 온다.
      queryClient.setQueryData<InquiryItem[]>(inquiriesQueryKey(), (current = []) => [
        created,
        ...current,
      ]);
      queryClient.setQueryData(inquiryQueryKey(created.id), created);
    },
  });
}

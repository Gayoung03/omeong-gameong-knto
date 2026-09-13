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
      // 새 문의를 바로 보여주고(최신순이라 맨 앞), 서버 기준으로 다시 맞춘다.
      queryClient.setQueryData<InquiryItem[]>(inquiriesQueryKey(), (current = []) => [
        created,
        ...current,
      ]);
      queryClient.setQueryData(inquiryQueryKey(created.id), created);
      void queryClient.invalidateQueries({ queryKey: inquiriesQueryKey() });
    },
  });
}

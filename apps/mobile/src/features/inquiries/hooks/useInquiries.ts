import { useQuery } from '@tanstack/react-query';

import type { InquiryItem } from '@/src/types/inquiry';

import { fetchInquiries, fetchInquiry } from '../services/inquiryService';

export function inquiriesQueryKey() {
  return ['inquiries', 'list'] as const;
}

export function inquiryQueryKey(inquiryId: string) {
  return ['inquiries', 'detail', inquiryId] as const;
}

export function useInquiries() {
  return useQuery<InquiryItem[]>({
    queryKey: inquiriesQueryKey(),
    queryFn: fetchInquiries,
  });
}

export function useInquiry(inquiryId: string) {
  return useQuery<InquiryItem>({
    queryKey: inquiryQueryKey(inquiryId),
    queryFn: () => fetchInquiry(inquiryId),
    enabled: Boolean(inquiryId),
  });
}

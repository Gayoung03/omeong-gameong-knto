import { useLocalSearchParams } from 'expo-router';

import { InquiryDetailScreen } from '@/src/features/inquiries/InquiryDetailScreen';

export default function InquiryDetailRoute() {
  const { inquiryId } = useLocalSearchParams<{ inquiryId: string }>();

  return <InquiryDetailScreen inquiryId={inquiryId} />;
}

import { useLocalSearchParams } from 'expo-router';

import { EditorialStoryScreen } from '@/src/features/home/screens/EditorialStoryScreen';

export default function EditorialStoryRoute() {
  const { storyId } = useLocalSearchParams<{ storyId: string }>();

  return <EditorialStoryScreen storyId={storyId ?? ''} />;
}

import { useLocalSearchParams } from 'expo-router';

import { PetFormScreen } from '@/src/features/profile/PetFormScreen';

export default function PetEditRoute() {
  const { petId } = useLocalSearchParams<{ petId: string }>();

  return <PetFormScreen petId={petId} />;
}

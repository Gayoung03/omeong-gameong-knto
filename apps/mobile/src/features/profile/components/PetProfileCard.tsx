import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { Card } from '@/src/components/ui/Card';
import { colors, spacing, typography } from '@/src/theme';
import type { Pet } from '@/src/types/pet';

type PetProfileCardProps = {
  pet: Pet;
};

export function PetProfileCard({ pet }: PetProfileCardProps) {
  const router = useRouter();
  // 수정 화면은 언제나 petId로 연다. 이름은 중복될 수 있어 식별자로 쓰지 않는다.
  const openEditScreen = () => router.push({ pathname: '/pets/[petId]', params: { petId: pet.petId } });

  return (
    // TODO: 반려동물 상세 화면 연결
    <Pressable>
      <Card style={styles.card}>
        <Pressable
          accessibilityLabel={`${pet.name} 프로필 수정`}
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={openEditScreen}
          style={styles.editButton}
        >
          <Ionicons color={colors.textSecondary} name="create-outline" size={18} />
        </Pressable>
        <Avatar size={56} uri={pet.profileImage} />
        <View style={styles.info}>
          <Text style={styles.name}>{pet.name}</Text>
          <Text style={styles.detail}>
            {pet.species} · {pet.breed}
          </Text>
          <Text style={styles.detail}>
            {pet.age}세 · {pet.weight}kg
          </Text>
        </View>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    flexDirection: 'row',
  },
  detail: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    marginTop: spacing.xs / 2,
  },
  editButton: {
    position: 'absolute',
    right: spacing.sm,
    top: spacing.sm,
    zIndex: 1,
  },
  info: {
    flex: 1,
    marginLeft: spacing.md,
  },
  name: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
});

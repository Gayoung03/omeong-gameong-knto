import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { Card } from '@/src/components/ui/Card';
import { colors, spacing, typography } from '@/src/theme';
import { formatSpecies, type Pet } from '@/src/types/pet';

type PetProfileCardProps = {
  pet: Pet;
};

export function PetProfileCard({ pet }: PetProfileCardProps) {
  const router = useRouter();
  // 수정 화면은 언제나 petId로 연다. 이름은 중복될 수 있어 식별자로 쓰지 않는다.
  const openEditScreen = () => router.push({ pathname: '/pets/[petId]', params: { petId: pet.petId } });

  return (
    /*
     * 카드 어디를 눌러도 수정 화면으로 간다.
     * 연필은 그 사실을 알려주는 표시라 따로 Pressable 로 감싸지 않는다.
     * (버튼을 중첩하면 웹에서 오류가 난다)
     */
    <Pressable
      accessibilityLabel={`${pet.name} 프로필 수정`}
      accessibilityRole="button"
      onPress={openEditScreen}
      style={({ pressed }) => pressed && styles.pressed}
    >
      <Card style={styles.card}>
        <View style={styles.editIcon}>
          <Ionicons color={colors.textSecondary} name="create-outline" size={18} />
        </View>
        <Avatar size={56} uri={pet.profileImage} />
        <View style={styles.info}>
          <Text style={styles.name}>{pet.name}</Text>
          <Text style={styles.detail}>
            {formatSpecies(pet)} · {pet.breed}
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
  editIcon: {
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
  pressed: {
    opacity: 0.7,
  },
});

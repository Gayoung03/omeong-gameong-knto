import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
} from 'react-native';

import { colors } from '@/src/theme';

type FormFieldProps = TextInputProps & {
  icon: keyof typeof Ionicons.glyphMap;
  error?: string;
  password?: boolean;
};

export function FormField({ icon, error, password = false, style, ...props }: FormFieldProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);

  return (
    <View style={styles.wrapper}>
      <View style={[styles.field, error && styles.fieldError]}>
        <Ionicons color="#929292" name={icon} size={21} />
        <TextInput
          autoCapitalize="none"
          placeholderTextColor="#A7A7A7"
          secureTextEntry={password && !passwordVisible}
          style={[styles.input, style]}
          {...props}
        />
        {password && (
          <Pressable
            accessibilityLabel={passwordVisible ? '비밀번호 숨기기' : '비밀번호 보기'}
            hitSlop={10}
            onPress={() => setPasswordVisible((visible) => !visible)}
          >
            <Ionicons
              color="#929292"
              name={passwordVisible ? 'eye-off-outline' : 'eye-outline'}
              size={21}
            />
          </Pressable>
        )}
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: 5,
  },
  field: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: '#E4E1DE',
    borderRadius: 15,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 11,
    minHeight: 58,
    paddingHorizontal: 17,
  },
  fieldError: {
    borderColor: colors.error,
  },
  input: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: 15,
    minWidth: 0,
    paddingVertical: 14,
  },
  error: {
    color: colors.error,
    fontSize: 12,
    marginLeft: 4,
  },
});

import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, type TextInputProps, View } from 'react-native';

import { colors } from '@/src/theme';

type IconTextFieldProps = TextInputProps & {
  icon: keyof typeof Ionicons.glyphMap;
  error?: string;
  password?: boolean;
};

/** 아이콘 + 입력창 한 덩어리. 비밀번호 토글과 오류 문구를 포함한다. */
export function IconTextField({
  icon,
  error,
  password = false,
  style,
  ...props
}: IconTextFieldProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);

  return (
    <View style={styles.wrapper}>
      <View style={[styles.field, error && styles.fieldError]}>
        <Ionicons color={colors.iconGray} name={icon} size={21} />
        <TextInput
          autoCapitalize="none"
          placeholderTextColor={colors.textTertiary}
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
              color={colors.iconGray}
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
    borderColor: colors.divider,
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

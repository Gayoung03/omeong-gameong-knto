import { Platform } from 'react-native';

export const shadow = {
  sm: Platform.select({
    web: {
      boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.06)',
    },
    default: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.06,
      shadowRadius: 3,
      elevation: 2,
    },
  }),
} as const;

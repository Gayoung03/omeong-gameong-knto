export type PetType = 'dog' | 'cat' | 'rabbit' | 'bird' | 'other';

export type PetSize = 'small' | 'medium' | 'large';

/**
 * 회원가입 시 받는 동의 항목.
 * marketing 을 제외한 나머지는 필수라 하나라도 false 면 가입을 진행할 수 없다.
 */
export type SignupAgreements = {
  age14: boolean;
  terms: boolean;
  privacy: boolean;
  marketing: boolean;
};

export type SignupData = {
  agreements: SignupAgreements;
  account: {
    email: string;
    password: string;
    passwordConfirm: string;
    nickname: string;
  };
  pet: {
    type: PetType | null;
    size: PetSize | null;
  };
  travel: {
    duration: string | null;
    transport: string | null;
    departure: string;
    vibes: string[];
    companions: number;
  };
};

export type PetType = 'dog' | 'cat' | 'rabbit' | 'bird' | 'other';

export type PetSize = 'small' | 'medium' | 'large';

export type SignupData = {
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

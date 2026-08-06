export type PetFormValues = {
  name: string;
  breed: string;
  /** 입력 원문. 검증 시점에 파싱한다. */
  age: string;
  weight: string;
};

export type PetFormErrors = {
  name?: string;
  breed?: string;
  age?: string;
  weight?: string;
};

const NAME_MAX = 10;
const BREED_MAX = 20;
const AGE_MAX = 30;
const WEIGHT_MIN = 0.1;
const WEIGHT_MAX = 100;

export function validatePetForm(values: PetFormValues): PetFormErrors {
  const errors: PetFormErrors = {};

  const name = values.name.trim();
  if (name.length === 0) {
    errors.name = '이름을 입력해 주세요';
  } else if (name.length > NAME_MAX) {
    errors.name = `이름은 ${NAME_MAX}자 이하로 입력해 주세요`;
  }

  const breed = values.breed.trim();
  if (breed.length === 0) {
    errors.breed = '품종을 입력해 주세요';
  } else if (breed.length > BREED_MAX) {
    errors.breed = `품종은 ${BREED_MAX}자 이하로 입력해 주세요`;
  }

  const age = Number(values.age.trim());
  if (values.age.trim().length === 0) {
    errors.age = '나이를 입력해 주세요';
  } else if (!Number.isInteger(age) || age < 0 || age > AGE_MAX) {
    errors.age = `나이는 0~${AGE_MAX}세 사이 정수로 입력해 주세요`;
  }

  const weight = Number(values.weight.trim());
  if (values.weight.trim().length === 0) {
    errors.weight = '몸무게를 입력해 주세요';
  } else if (Number.isNaN(weight) || weight < WEIGHT_MIN || weight > WEIGHT_MAX) {
    errors.weight = `몸무게는 ${WEIGHT_MIN}~${WEIGHT_MAX}kg 사이로 입력해 주세요`;
  } else if (Math.round(weight * 10) !== weight * 10) {
    errors.weight = '몸무게는 소수점 첫째 자리까지 입력해 주세요';
  }

  return errors;
}

export function hasPetFormError(errors: PetFormErrors): boolean {
  return Object.values(errors).some((message) => message !== undefined);
}

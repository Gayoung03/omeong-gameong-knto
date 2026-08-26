export type PetFormValues = {
  name: string;
  /** '기타'를 골랐을 때 입력한 종 이름. 그 외에는 검사하지 않는다. */
  speciesDetail?: string;
  breed: string;
  birthDate: string;
  weight: string;
};

export type PetFormErrors = {
  name?: string;
  speciesDetail?: string;
  breed?: string;
  birthDate?: string;
  weight?: string;
};

const NAME_MAX = 10;
const SPECIES_DETAIL_MAX = 20;
const BREED_MAX = 20;
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

  // '기타'가 아니면 speciesDetail 자체를 넘기지 않으므로 undefined 는 통과시킨다.
  if (values.speciesDetail !== undefined) {
    const speciesDetail = values.speciesDetail.trim();
    if (speciesDetail.length === 0) {
      errors.speciesDetail = '종 이름을 입력해 주세요';
    } else if (speciesDetail.length > SPECIES_DETAIL_MAX) {
      errors.speciesDetail = `종 이름은 ${SPECIES_DETAIL_MAX}자 이하로 입력해 주세요`;
    }
  }

  const breed = values.breed.trim();
  if (breed.length === 0) {
    errors.breed = '품종을 입력해 주세요';
  } else if (breed.length > BREED_MAX) {
    errors.breed = `품종은 ${BREED_MAX}자 이하로 입력해 주세요`;
  }

  const birthDate = values.birthDate.trim();
  const parsedBirthDate = new Date(`${birthDate}T00:00:00Z`);
  if (birthDate.length === 0) {
    errors.birthDate = '생년월일을 입력해 주세요';
  } else if (
    !/^\d{4}-\d{2}-\d{2}$/.test(birthDate) ||
    Number.isNaN(parsedBirthDate.getTime()) ||
    parsedBirthDate.toISOString().slice(0, 10) !== birthDate
  ) {
    errors.birthDate = 'YYYY-MM-DD 형식의 올바른 날짜를 입력해 주세요';
  } else {
    const today = new Date();
    const todayText = [
      today.getFullYear(),
      String(today.getMonth() + 1).padStart(2, '0'),
      String(today.getDate()).padStart(2, '0'),
    ].join('-');
    if (birthDate > todayText) errors.birthDate = '미래 날짜는 입력할 수 없어요';
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

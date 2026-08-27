export const chatbotSuggestions = [
  {
    id: 'pet-friendly-stay',
    icon: 'bed-outline',
    question: '반려동물 동반 가능 숙소 추천해줘',
  },
  {
    id: 'aewol-cafe',
    icon: 'cafe-outline',
    question: '애월에서 강아지와 갈 수 있는 카페 알려줘',
  },
  {
    id: 'rainy-day',
    icon: 'rainy-outline',
    question: '비 오는 날 함께 갈 실내 관광지 추천해줘',
  },
  {
    // "주변"은 물을 수 없다 — 개인위치정보를 수집하지 않기로 확정해서 사용자가
    // 어디 있는지 모른다. 답할 수 없는 질문을 권하지 않도록 지역을 넣었다.
    id: 'animal-hospital',
    icon: 'medkit-outline',
    question: '제주시에 반려동물 병원 알려줘',
  },
  {
    id: 'walking-place',
    icon: 'paw-outline',
    question: '제주에서 반려견과 산책하기 좋은 곳은?',
  },
] as const;

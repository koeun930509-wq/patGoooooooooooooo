"""KorPetTourService2 관련 상수 및 판정 규칙에 쓰이는 고정값 모음."""

BASE_URL = "http://apis.data.go.kr/B551011/KorPetTourService2"
MOBILE_OS = "ETC"
MOBILE_APP = "PetGo"

# 관광타입 필터 (탐색 화면)
CONTENT_TYPES = {
    12: "관광지",
    14: "문화시설",
    15: "행사",
    28: "레포츠",
    32: "숙박",
    38: "쇼핑",
    39: "음식점",
}

# 크기 카테고리 ↔ 대표 체중 상한(kg). acmpyPsblCpam에 숫자 없이
# "소형견/중형견/대형견"만 표기된 경우 이 값과 비교해 조건부 판정에 사용한다.
SIZE_WEIGHT_THRESHOLDS = {
    "소형": 10,
    "중형": 25,
    "대형": None,  # 상한 없음
}

# 크기 선택 UI ↔ 체중 슬라이더 초기값(참고용)
PET_SIZE_OPTIONS = ["소형", "중형", "대형"]

# acmpyNeedMtr / etcAcmpyInfo 자유 텍스트에서 준비물 키워드를 추출하기 위한 매핑.
# key: 체크리스트에 표시할 항목명, value: 원문에서 매칭할 키워드들
CHECKLIST_KEYWORDS = {
    "목줄/리드줄": ["목줄", "리드줄"],
    "입마개": ["입마개"],
    "이동장/캐리어": ["이동장", "캐리어"],
    "배변봉투": ["배변봉투", "배변 봉투", "배변처리"],
    "예방접종 증명서": ["예방접종", "접종증명"],
    "인식표": ["인식표"],
    "반려동물 등록증": ["등록증"],
}

# 동반 자체를 명시적으로 금지하는 키워드 (acmpyPsblCpam / etcAcmpyInfo)
DISALLOW_KEYWORDS = ["동반 불가", "동반불가", "출입금지", "출입 금지", "반입금지", "반입 금지", "동반 제한"]

# 전 견종/전체 동물 허용을 나타내는 키워드
ALL_ALLOWED_KEYWORDS = ["전 견종", "전견종", "모든 동물", "전체 동물", "품종 무관"]

# 구역/장소 제한을 나타내는 키워드 (acmpyTypeCd)
PARTIAL_AREA_KEYWORDS = ["일부구역", "일부 구역", "실외만", "실외석", "테라스만"]

# 맹견 관련 키워드
DANGEROUS_BREED_KEYWORDS = ["맹견"]
MUZZLE_KEYWORDS = ["입마개"]

# 무게 상한 정규식이 매칭할 단위 표현 ("10kg 이하", "10kg 미만" 등)
WEIGHT_LIMIT_PATTERN = r"(\d+(?:\.\d+)?)\s*kg\s*(이하|미만|이내)"

VERDICT_BADGES = {
    "가능": "🟢 가능",
    "조건부 가능": "🟡 조건부 가능",
    "불가": "🔴 불가",
    "정보 부족": "⚪ 정보 부족",
}

DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5-20251001"

REPORTS_CSV_PATH = "data/reports.csv"

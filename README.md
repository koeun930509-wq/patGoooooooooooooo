# PetGo — 반려동물 동반 여행 가이드 (MVP)

반려동물 프로필(견종·무게·맹견 여부 등)과 한국관광공사 `KorPetTourService2` 규정을 대조해
동반 가능 여부(🟢 가능 / 🟡 조건부 가능 / 🔴 불가 / ⚪ 정보 부족)와 필수 준비물을 판정해주는 Streamlit MVP입니다.

## 폴더 구조

```
app.py                        # 엔트리포인트, 화면 라우팅
pet_guide/
  constants.py                 # contentTypeId, 판정 키워드/임계값
  models.py                     # PetProfile / PlaceSummary / PlaceDetail / JudgeResult
  api_client.py                 # KorPetTourService2 프록시 + 캐싱 (서비스키는 여기서만 사용)
  judge.py                      # 1차 결정적 규칙 판정 엔진
  llm_interpreter.py            # 2차 Claude API 판정 엔진 (모호 케이스만 호출)
  ui/
    profile_screen.py           # 반려동물 프로필 등록/선택
    explore_screen.py           # 지역/내주변/키워드 탐색
    detail_screen.py            # 판정 배지·체크리스트·주의사항·원문·오판정 신고
tests/test_judge.py             # 판정 엔진 단위 테스트 (데모 3종 포함)
```

## 로컬 실행 방법

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows(Git Bash) — PowerShell은 .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
# .env를 열어 SERVICE_KEY(data.go.kr), ANTHROPIC_API_KEY(선택) 입력

streamlit run app.py
```

## 환경변수

| 변수 | 설명 |
|---|---|
| `SERVICE_KEY` | 공공데이터포털에서 발급받은 `KorPetTourService2` 서비스키(Decoding 키). 없으면 탐색/판정이 동작하지 않습니다. |
| `ANTHROPIC_API_KEY` | Claude API 키. 규칙으로 확정되지 않는 모호한 원문 규정 해석에만 사용됩니다. 없어도 앱은 동작하며, 이 경우 모호 케이스는 "정보 부족"으로 처리됩니다. |
| `CLAUDE_MODEL` | 선택. 해석 엔진에 사용할 모델 (기본값 `claude-haiku-4-5-20251001`). |

Streamlit Community Cloud에 배포할 경우 `.streamlit/secrets.toml.example`을 참고해 앱의 Secrets 설정에 동일한 키를 등록하세요.

## 테스트

```bash
pytest tests/ -v
```

`tests/test_judge.py`는 판정 엔진만 목데이터로 검증하며, 아래 데모 시나리오를 포함합니다.

1. **소형견 카페 방문** — 4kg 소형견, "소형견만 동반 가능" → 🟢 가능
2. **대형견 관광지 방문** — 32kg 대형견, "소형견만 동반 가능" → 🟡 조건부 가능(현장 확인 권장)
3. **맹견 숙박시설 방문** — 맹견, "전 견종 가능(맹견은 입마개 필수)" → 🟡 조건부 가능 + 입마개 체크리스트

## 판정 로직 개요

1. `judge.py`가 원문(`acmpyTypeCd`/`acmpyPsblCpam`/`acmpyNeedMtr`/`etcAcmpyInfo`)에 결정적 규칙을 적용합니다
   (명시적 금지 키워드, 숫자 체중 제한, 소/중/대형 카테고리, 맹견+입마개, 구역/실외 제한, 빈 필드 → 정보 부족).
2. 규칙으로 확정되지 않는 모호한 텍스트만 `llm_interpreter.py`가 Claude API로 해석합니다(원문에 없는 조건은 생성하지 않도록 제약된 시스템 프롬프트 사용).
3. `ANTHROPIC_API_KEY`가 없거나 호출이 실패하면 "정보 부족 + 현장 확인 권장"으로 안전하게 폴백합니다.

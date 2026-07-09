"""2차 해석 엔진: 규칙으로 확정되지 않은 모호한 원문만 Claude API로 해석한다.

시스템 프롬프트는 개발프롬프트.md의 "B. 조건 해석 엔진 프롬프트"를 그대로 사용한다.
ANTHROPIC_API_KEY가 없으면 조용히 None을 반환해 judge.py가 규칙 기반 폴백으로 처리하게 한다.
"""

import json
import os
import re

import streamlit as st

from pet_guide.constants import DEFAULT_CLAUDE_MODEL
from pet_guide.models import JudgeResult, PetProfile, PlaceDetail

SYSTEM_PROMPT = """너는 반려동물 동반 여행 규정을 해석하는 판정 엔진이다.
입력으로 (1) 반려동물 프로필과 (2) 한국관광공사 detailPetTour2 원문 규정을 받는다.
목표는 이 반려동물이 이 장소에 동반 입장 가능한지 명확히 판정하고, 필요한 준비물을 안내하는 것이다.

[반드시 지킬 규칙]
1. 원문(입력된 규정)에 근거해서만 판정한다. 원문에 없는 조건·시설·요구사항을 지어내지 않는다.
2. 정보가 없거나 모호해 판단 불가하면 verdict를 "정보 부족"으로 하고 "현장 확인 권장"을 안내한다.
3. 경계가 애매하면(예: 무게 기준이 불명확) 보수적으로 "조건부 가능"으로 판정한다.
4. 견종·무게·맹견 여부를 반드시 규정과 대조한다.
   - 규정에 "소형견만" 류가 있고 무게가 큰 경우 → 조건부/불가
   - "맹견 입마개 필수" 류가 있고 맹견인 경우 → 조건부 가능(입마개 준비물 추가)
   - "전 견종 동반 가능"이면 특성 무관 가능(그 외 공통 준비물만)
5. 준비물은 규정에서 요구한 항목(목줄/목줄 길이·입마개·배변봉투·이동장 등)만 반영하고, 반려동물 특성에 맞게 조정한다.
6. 과장·불안 조장 없이, 짧고 명확한 한국어로 쓴다.

[출력 형식] 아래 JSON만 반환한다. 그 외 텍스트·설명·마크다운 금지.
{
  "verdict": "가능" | "조건부 가능" | "불가" | "정보 부족",
  "reason": "판정 근거 1~2문장",
  "checklist": ["필수 준비물 항목", "..."],
  "cautions": ["주의사항", "..."],
  "source_quote": "판정 근거가 된 원문 일부(없으면 빈 문자열)"
}"""


def _api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return ""


def _model() -> str:
    model = os.environ.get("CLAUDE_MODEL")
    if model:
        return model
    try:
        return st.secrets.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    except Exception:
        return DEFAULT_CLAUDE_MODEL


def _strip_code_fence(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def _build_user_payload(profile: PetProfile, detail: PlaceDetail) -> str:
    payload = {
        "반려동물": {
            "견종": profile.breed,
            "무게": profile.weight_kg,
            "크기": profile.size,
            "맹견여부": profile.is_dangerous_breed,
            "입마개가능": profile.can_wear_muzzle,
        },
        "규정": {
            "acmpyTypeCd": detail.acmpy_type_cd,
            "acmpyPsblCpam": detail.acmpy_psbl_cpam,
            "acmpyNeedMtr": detail.acmpy_need_mtr,
            "etcAcmpyInfo": detail.etc_acmpy_info,
            "relaAcdntRiskMtr": detail.rela_acdnt_risk_mtr,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def interpret(profile: PetProfile, detail: PlaceDetail) -> JudgeResult | None:
    api_key = _api_key()
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_model(),
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_payload(profile, detail)}],
        )
        raw_text = response.content[0].text
        data = json.loads(_strip_code_fence(raw_text))
    except Exception as exc:
        st.warning(f"AI 조건 해석 엔진 호출에 실패해 규칙 기반 결과로 대체합니다: {exc}")
        return None

    return JudgeResult(
        verdict=data.get("verdict", "정보 부족"),
        reason=data.get("reason", ""),
        checklist=list(data.get("checklist", [])),
        cautions=list(data.get("cautions", [])),
        source_quote=data.get("source_quote", ""),
        source="llm",
    )

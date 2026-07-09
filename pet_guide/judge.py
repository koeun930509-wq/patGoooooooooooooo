"""판정 로직: 1차 결정적 규칙 필터 → 확정 안 되면 2차 LLM 해석(llm_interpreter)으로 위임.

규칙 예시는 PRD `PRD_반려동물동반여행가이드.md` 8.1절 및 개발프롬프트.md [판정 로직] 절을 그대로 구현한다.
"""

import re

from pet_guide.constants import (
    ALL_ALLOWED_KEYWORDS,
    CHECKLIST_KEYWORDS,
    DANGEROUS_BREED_KEYWORDS,
    DISALLOW_KEYWORDS,
    MUZZLE_KEYWORDS,
    PARTIAL_AREA_KEYWORDS,
    SIZE_WEIGHT_THRESHOLDS,
    WEIGHT_LIMIT_PATTERN,
)
from pet_guide.models import JudgeResult, PetProfile, PlaceDetail

_SEVERITY_TO_VERDICT = {3: "불가", 2: "조건부 가능", 1: "가능"}


def _extract_checklist(text: str) -> list[str]:
    items = []
    for label, keywords in CHECKLIST_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            items.append(label)
    return items


def _apply_rules(profile: PetProfile, detail: PlaceDetail) -> JudgeResult | None:
    """규칙으로 확정되면 JudgeResult, 확정 불가(모호)면 None을 반환한다."""
    type_cd = detail.acmpy_type_cd
    psbl_cpam = detail.acmpy_psbl_cpam
    need_mtr = detail.acmpy_need_mtr
    etc_info = detail.etc_acmpy_info
    combined = " ".join(f for f in (type_cd, psbl_cpam, need_mtr, etc_info) if f)

    if not combined.strip():
        return JudgeResult(
            verdict="정보 부족",
            reason="이 장소의 반려동물 동반 조건에 대한 원문 정보가 등록되어 있지 않습니다.",
            cautions=["현장 확인 권장"],
            source="rule",
        )

    hits: list[tuple[int, str, list[str], list[str], str]] = []  # severity, reason, cautions, checklist, quote

    # 1. 명시적 동반 금지
    for kw in DISALLOW_KEYWORDS:
        if kw in psbl_cpam or kw in etc_info:
            hits.append((3, f"'{kw}' 조건이 명시되어 있어 동반이 불가합니다.", [], [], kw))
            break

    # 2. 숫자 체중 제한 (예: "10kg 이하")
    weight_match = re.search(WEIGHT_LIMIT_PATTERN, f"{psbl_cpam} {etc_info}")
    if weight_match:
        limit = float(weight_match.group(1))
        quote = weight_match.group(0)
        if profile.weight_kg <= limit:
            hits.append((1, f"체중 기준({quote}) 이내로 동반 가능합니다.", [], [], quote))
        elif profile.weight_kg <= limit * 1.1:
            hits.append(
                (
                    2,
                    f"체중 기준({quote})을 근소하게 초과하여 조건부로 판정합니다.",
                    ["현장 확인 권장"],
                    [],
                    quote,
                )
            )
        else:
            hits.append((3, f"체중 기준({quote})을 초과하여 동반이 어려울 수 있습니다.", [], [], quote))
    else:
        # 3. 숫자 제한이 없을 때만 크기 카테고리(소형/중형/대형)로 판단
        mentioned = [size for size in SIZE_WEIGHT_THRESHOLDS if size in psbl_cpam]
        has_all_keyword = any(kw in psbl_cpam for kw in ALL_ALLOWED_KEYWORDS)
        if mentioned and not has_all_keyword:
            thresholds = [SIZE_WEIGHT_THRESHOLDS[s] for s in mentioned]
            if None not in thresholds:  # "대형견"까지 언급되면 체중 상한 없음 -> 규칙 미적용
                max_allowed = max(thresholds)
                label = "/".join(f"{s}견" for s in mentioned)
                if profile.weight_kg <= max_allowed:
                    hits.append((1, f"'{label}' 기준에 부합하여 동반 가능합니다.", [], [], label))
                else:
                    hits.append(
                        (
                            2,
                            f"'{label}'만 명시되어 있고 체중이 기준을 초과하여 조건부로 판정합니다.",
                            ["현장 확인 권장"],
                            [],
                            label,
                        )
                    )

    # 4. 맹견 + 입마개 (이 반려동물이 맹견일 때만 적용)
    if profile.is_dangerous_breed and any(kw in combined for kw in DANGEROUS_BREED_KEYWORDS):
        if any(kw in combined for kw in MUZZLE_KEYWORDS):
            if profile.can_wear_muzzle:
                hits.append((2, "맹견은 입마개 착용 시 동반 가능합니다.", [], ["입마개"], "맹견"))
            else:
                hits.append(
                    (
                        2,
                        "맹견은 입마개 착용이 필요합니다.",
                        ["입마개 착용 불가로 설정되어 있어 현장 진입이 어려울 수 있습니다."],
                        ["입마개"],
                        "맹견",
                    )
                )
        else:
            hits.append((2, "맹견에 대한 조건이 명시되어 있어 조건부로 판정합니다.", ["현장 확인 권장"], [], "맹견"))

    # 5. 구역/실외 제한
    if any(kw in type_cd for kw in PARTIAL_AREA_KEYWORDS):
        hits.append((2, "일부 구역 또는 실외에서만 동반이 가능합니다.", [], [], type_cd))

    # 6. 전 견종/전체 동물 허용 (다른 규칙이 아무것도 안 걸렸을 때만 단독 판정)
    if not hits and any(kw in psbl_cpam for kw in ALL_ALLOWED_KEYWORDS):
        hits.append((1, "전 견종/전체 동물 동반이 가능한 장소입니다.", [], [], psbl_cpam))

    if not hits:
        return None  # 규칙으로 확정 불가 -> LLM 해석으로 위임

    final_severity = max(h[0] for h in hits)
    verdict = _SEVERITY_TO_VERDICT[final_severity]
    top_reasons = [h[1] for h in hits if h[0] == final_severity]

    cautions: list[str] = []
    checklist = _extract_checklist(combined)
    quotes: list[str] = []
    for _, _, hit_cautions, hit_checklist, quote in hits:
        cautions.extend(hit_cautions)
        checklist.extend(hit_checklist)
        if quote:
            quotes.append(quote)
    if detail.rela_acdnt_risk_mtr:
        cautions.append(detail.rela_acdnt_risk_mtr)

    return JudgeResult(
        verdict=verdict,
        reason=" ".join(dict.fromkeys(top_reasons)),
        checklist=list(dict.fromkeys(checklist)),
        cautions=list(dict.fromkeys(cautions)),
        source_quote=" / ".join(dict.fromkeys(quotes)),
        source="rule",
    )


def judge_pet(profile: PetProfile, detail: PlaceDetail) -> JudgeResult:
    rule_result = _apply_rules(profile, detail)
    if rule_result is not None:
        return rule_result

    from pet_guide.llm_interpreter import interpret  # 지연 임포트: LLM 호출은 모호할 때만 필요

    llm_result = interpret(profile, detail)
    if llm_result is not None:
        return llm_result

    return JudgeResult(
        verdict="정보 부족",
        reason="원문 규정이 모호하여 명확히 판정할 수 없습니다.",
        cautions=["현장 확인 권장"],
        source="rule",
    )

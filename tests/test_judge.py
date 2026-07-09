"""judge_pet() 단위 테스트 — 데모 시나리오 3종 + 경계 케이스.

네트워크 호출 없이 PlaceDetail을 목데이터로 직접 구성해 규칙 엔진만 검증한다.
ANTHROPIC_API_KEY가 없는 환경에서도(CI 등) 규칙으로 확정되는 케이스는 전부 통과해야 한다.
"""

import os

from pet_guide.judge import judge_pet
from pet_guide.models import PetProfile, PlaceDetail


def _detail(**overrides) -> PlaceDetail:
    base = dict(
        content_id="1",
        content_type_id="39",
        title="테스트 장소",
        addr="서울시 어딘가",
        tel=None,
        overview=None,
        image_url=None,
        map_x=None,
        map_y=None,
        use_time=None,
        rest_date=None,
        parking=None,
    )
    base.update(overrides)
    return PlaceDetail(**base)


def test_small_dog_cafe_allowed():
    """데모 1: 소형견(4kg)이 '소형견만 동반 가능' 카페 방문 -> 가능."""
    pet = PetProfile(
        name="콩이", species="개", breed="말티즈", weight_kg=4.0, size="소형",
        is_dangerous_breed=False, can_wear_muzzle=False,
    )
    detail = _detail(
        content_type_id="39",
        acmpy_psbl_cpam="소형견만 동반 가능",
        acmpy_need_mtr="목줄 착용",
    )
    result = judge_pet(pet, detail)
    assert result.verdict == "가능"
    assert "목줄/리드줄" in result.checklist


def test_large_dog_tourist_site_conditional():
    """데모 2: 대형견(32kg)이 '소형견만 동반 가능' 관광지 방문 -> 조건부(보수적 판정)."""
    pet = PetProfile(
        name="바우", species="개", breed="골든리트리버", weight_kg=32.0, size="대형",
        is_dangerous_breed=False, can_wear_muzzle=False,
    )
    detail = _detail(
        content_type_id="12",
        acmpy_psbl_cpam="소형견만 동반 가능",
    )
    result = judge_pet(pet, detail)
    assert result.verdict == "조건부 가능"
    assert "현장 확인 권장" in result.cautions


def test_dangerous_breed_lodging_requires_muzzle():
    """데모 3: 맹견이 '전 견종 가능(맹견은 입마개 필수)' 숙박시설 방문 -> 조건부 + 입마개 체크리스트."""
    pet = PetProfile(
        name="독이", species="개", breed="도베르만", weight_kg=30.0, size="대형",
        is_dangerous_breed=True, can_wear_muzzle=True,
    )
    detail = _detail(
        content_type_id="32",
        acmpy_type_cd="전구역 동반가능",
        acmpy_psbl_cpam="전 견종 동반 가능(맹견의 경우, 입마개 착용 필수)",
        acmpy_need_mtr="목줄 착용",
        etc_acmpy_info="배변봉투 지참 및 배변처리 필수",
    )
    result = judge_pet(pet, detail)
    assert result.verdict == "조건부 가능"
    assert "입마개" in result.checklist
    assert "목줄/리드줄" in result.checklist
    assert "배변봉투" in result.checklist


def test_explicit_disallow_keyword():
    pet = PetProfile(
        name="초코", species="개", breed="비숑", weight_kg=6.0, size="소형",
        is_dangerous_breed=False, can_wear_muzzle=False,
    )
    detail = _detail(acmpy_psbl_cpam="반려동물 동반불가 시설")
    result = judge_pet(pet, detail)
    assert result.verdict == "불가"


def test_empty_fields_is_information_lacking():
    pet = PetProfile(
        name="루비", species="고양이", breed="코숏", weight_kg=3.5, size="소형",
        is_dangerous_breed=False, can_wear_muzzle=False,
    )
    detail = _detail()
    result = judge_pet(pet, detail)
    assert result.verdict == "정보 부족"
    assert "현장 확인 권장" in result.cautions


def test_ambiguous_free_text_falls_back_gracefully_without_llm_key(monkeypatch):
    """규칙에 걸리지 않는 모호한 자유 텍스트 + LLM 키 없음 -> 예외 없이 '정보 부족'으로 폴백."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    pet = PetProfile(
        name="나비", species="개", breed="시바견", weight_kg=9.0, size="소형",
        is_dangerous_breed=False, can_wear_muzzle=False,
    )
    detail = _detail(etc_acmpy_info="사전 문의 후 방문 권장, 상황에 따라 다를 수 있음")
    result = judge_pet(pet, detail)
    assert result.verdict == "정보 부족"

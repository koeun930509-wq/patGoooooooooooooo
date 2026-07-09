"""프로필 / 장소 / 판정 결과 데이터 구조."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PetProfile:
    name: str
    species: str  # "개" | "고양이" | "기타"
    breed: str
    weight_kg: float
    size: str  # "소형" | "중형" | "대형"
    is_dangerous_breed: bool
    can_wear_muzzle: bool
    vaccinated: Optional[bool] = None
    neutered: Optional[bool] = None


@dataclass
class PlaceSummary:
    content_id: str
    content_type_id: str
    title: str
    addr: str
    image_url: Optional[str]
    map_x: Optional[float]
    map_y: Optional[float]


@dataclass
class PlaceDetail:
    content_id: str
    content_type_id: str
    title: str
    addr: str
    tel: Optional[str]
    overview: Optional[str]
    image_url: Optional[str]
    map_x: Optional[float]
    map_y: Optional[float]
    use_time: Optional[str]
    rest_date: Optional[str]
    parking: Optional[str]
    # detailPetTour2 원문 필드
    acmpy_type_cd: str = ""
    acmpy_psbl_cpam: str = ""
    acmpy_need_mtr: str = ""
    etc_acmpy_info: str = ""
    rela_acdnt_risk_mtr: str = ""
    rela_poses_fclty: str = ""
    rela_frnsh_prdlst: str = ""
    rela_purc_prdlst: str = ""
    rela_rntl_prdlst: str = ""


@dataclass
class JudgeResult:
    verdict: str  # "가능" | "조건부 가능" | "불가" | "정보 부족"
    reason: str
    checklist: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    source_quote: str = ""
    source: str = "rule"  # "rule" | "llm"

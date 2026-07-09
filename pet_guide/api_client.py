"""KorPetTourService2 프록시 계층.

서비스키(serviceKey)는 이 모듈 안에서만 읽고 사용한다. Streamlit은 서버에서 렌더링되므로
클라이언트(브라우저)에는 이 키가 전혀 노출되지 않는다 — React+BFF 구성의 "서버에서만 키 사용"
요구사항을 Streamlit 프로세스 자체가 충족한다.

개발계정은 일 1,000건 트래픽 제한이 있으므로 모든 호출을 st.cache_data로 캐싱한다.
"""

import os

import requests
import streamlit as st

from pet_guide.constants import BASE_URL, MOBILE_APP, MOBILE_OS
from pet_guide.models import PlaceDetail, PlaceSummary

CACHE_TTL_SECONDS = 3600


def _service_key() -> str:
    key = os.environ.get("SERVICE_KEY")
    if key:
        return key
    try:
        return st.secrets["SERVICE_KEY"]
    except Exception:
        return ""


def _call(operation: str, params: dict) -> list[dict]:
    """TourAPI 오퍼레이션을 호출하고 item 리스트를 반환한다. 실패 시 빈 리스트."""
    service_key = _service_key()
    if not service_key:
        st.error("SERVICE_KEY가 설정되지 않았습니다. .env 또는 Streamlit secrets를 확인하세요.")
        return []

    query = {
        "serviceKey": service_key,
        "MobileOS": MOBILE_OS,
        "MobileApp": MOBILE_APP,
        "_type": "json",
        **params,
    }
    url = f"{BASE_URL}/{operation}"
    try:
        resp = requests.get(url, params=query, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        st.error(f"TourAPI 호출 실패({operation}): {exc}")
        return []

    if "response" not in payload:
        # 파라미터 오류 등으로 정상 응답 포맷이 아닌 에러 envelope가 온 경우
        # (예: {"resultCode": "10", "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR(...)"})
        message = payload.get("resultMsg") or payload.get("cmmMsgHeader", {}).get("errMsg") or payload
        st.error(f"TourAPI 오류({operation}): {message}")
        return []

    body = payload["response"]["body"]

    total_count = body.get("totalCount", 0)
    if not total_count:
        return []

    items = body.get("items", "")
    if not items:
        return []
    item = items.get("item", [])
    if isinstance(item, dict):
        return [item]
    return item


def _to_summary(item: dict) -> PlaceSummary:
    return PlaceSummary(
        content_id=str(item.get("contentid", "")),
        content_type_id=str(item.get("contenttypeid", "")),
        title=item.get("title", ""),
        addr=item.get("addr1", ""),
        image_url=item.get("firstimage") or None,
        map_x=float(item["mapx"]) if item.get("mapx") else None,
        map_y=float(item["mapy"]) if item.get("mapy") else None,
    )


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def area_based_list(
    l_dong_regn_cd: str = "",
    l_dong_signgu_cd: str = "",
    content_type_id: str = "",
    num_of_rows: int = 20,
    page_no: int = 1,
) -> list[PlaceSummary]:
    params = {
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "arrange": "A",
    }
    if l_dong_regn_cd:
        params["lDongRegnCd"] = l_dong_regn_cd
    if l_dong_signgu_cd:
        params["lDongSignguCd"] = l_dong_signgu_cd
    if content_type_id:
        params["contentTypeId"] = content_type_id
    items = _call("areaBasedList2", params)
    return [_to_summary(i) for i in items]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def location_based_list(
    map_x: float,
    map_y: float,
    radius: int = 3000,
    content_type_id: str = "",
    num_of_rows: int = 20,
    page_no: int = 1,
) -> list[PlaceSummary]:
    params = {
        "mapX": map_x,
        "mapY": map_y,
        "radius": radius,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "arrange": "E",
    }
    if content_type_id:
        params["contentTypeId"] = content_type_id
    items = _call("locationBasedList2", params)
    return [_to_summary(i) for i in items]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def search_keyword(
    keyword: str,
    content_type_id: str = "",
    num_of_rows: int = 20,
    page_no: int = 1,
) -> list[PlaceSummary]:
    params = {
        "keyword": keyword,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "arrange": "A",
    }
    if content_type_id:
        params["contentTypeId"] = content_type_id
    items = _call("searchKeyword2", params)
    return [_to_summary(i) for i in items]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def ldong_code(l_dong_regn_cd: str = "") -> list[dict]:
    """법정동 코드 조회. l_dong_regn_cd가 없으면 시/도 목록, 있으면 해당 시/도의 시/군/구 목록."""
    params = {"numOfRows": 50, "pageNo": 1}
    if l_dong_regn_cd:
        params["lDongRegnCd"] = l_dong_regn_cd
    return _call("ldongCode2", params)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def detail_common(content_id: str) -> dict:
    # KorPetTourService2의 detailCommon2는 TourAPI4.0(KorService2)과 달리
    # defaultYN/firstImageYN/addrinfoYN 등의 선택 파라미터를 받지 않는다.
    # 넘기면 INVALID_REQUEST_PARAMETER_ERROR로 응답 자체가 실패하므로 contentId만 전달한다.
    items = _call("detailCommon2", {"contentId": content_id})
    return items[0] if items else {}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def detail_intro(content_id: str, content_type_id: str) -> dict:
    if not content_type_id:
        return {}
    items = _call(
        "detailIntro2",
        {"contentId": content_id, "contentTypeId": content_type_id},
    )
    return items[0] if items else {}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def detail_pet_tour(content_id: str) -> dict:
    items = _call("detailPetTour2", {"contentId": content_id})
    return items[0] if items else {}


# detailIntro2는 콘텐츠 타입별로 운영시간/휴무/주차 필드명이 다르다.
_USE_TIME_FIELDS = ["usetime", "usetimeculture", "usetimeleports", "usetimefestival", "opentimefood", "usetimeshopping"]
_REST_DATE_FIELDS = ["restdate", "restdateculture", "restdateleports", "restdatefood", "restdateshopping"]
_PARKING_FIELDS = ["parking", "parkingculture", "parkingleports", "parkingfood", "parkingshopping"]


def _first_present(d: dict, keys: list[str]) -> str | None:
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def get_place_detail(content_id: str, content_type_id: str) -> PlaceDetail:
    common = detail_common(content_id)
    intro = detail_intro(content_id, content_type_id)
    pet = detail_pet_tour(content_id)

    return PlaceDetail(
        content_id=content_id,
        content_type_id=content_type_id,
        title=common.get("title", ""),
        addr=common.get("addr1", ""),
        tel=common.get("tel") or None,
        overview=common.get("overview") or None,
        image_url=common.get("firstimage") or None,
        map_x=float(common["mapx"]) if common.get("mapx") else None,
        map_y=float(common["mapy"]) if common.get("mapy") else None,
        use_time=_first_present(intro, _USE_TIME_FIELDS),
        rest_date=_first_present(intro, _REST_DATE_FIELDS),
        parking=_first_present(intro, _PARKING_FIELDS),
        acmpy_type_cd=pet.get("acmpyTypeCd", "") or "",
        acmpy_psbl_cpam=pet.get("acmpyPsblCpam", "") or "",
        acmpy_need_mtr=pet.get("acmpyNeedMtr", "") or "",
        etc_acmpy_info=pet.get("etcAcmpyInfo", "") or "",
        rela_acdnt_risk_mtr=pet.get("relaAcdntRiskMtr", "") or "",
        rela_poses_fclty=pet.get("relaPosesFclty", "") or "",
        rela_frnsh_prdlst=pet.get("relaFrnshPrdlst", "") or "",
        rela_purc_prdlst=pet.get("relaPurcPrdlst", "") or "",
        rela_rntl_prdlst=pet.get("relaRntlPrdlst", "") or "",
    )

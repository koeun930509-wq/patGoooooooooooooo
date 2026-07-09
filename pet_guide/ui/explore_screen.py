"""2) 탐색 화면: 지역 선택 / 내 주변 / 키워드 검색 탭 + 관광타입 필터 + 카드 리스트."""

import streamlit as st

from pet_guide import api_client
from pet_guide.constants import CONTENT_TYPES


def _code_and_name(item: dict) -> tuple[str, str]:
    code = item.get("code") or item.get("lDongRegnCd") or item.get("lDongSignguCd") or ""
    name = item.get("name") or item.get("lDongRegnNm") or item.get("lDongSignguNm") or code
    return code, name


def _content_type_filter(key: str) -> str:
    options = ["전체"] + list(CONTENT_TYPES.values())
    choice = st.selectbox("관광타입", options, key=key)
    if choice == "전체":
        return ""
    for cid, name in CONTENT_TYPES.items():
        if name == choice:
            return str(cid)
    return ""


def _render_results(results):
    if not results:
        st.info("검색 결과가 없습니다.")
        return
    st.caption(f"{len(results)}건의 결과")
    for place in results:
        with st.container(border=True):
            cols = st.columns([0.3, 0.7])
            with cols[0]:
                if place.image_url:
                    st.image(place.image_url, width="stretch")
                else:
                    st.markdown("🖼️ *이미지 없음*")
            with cols[1]:
                st.markdown(f"**{place.title}**")
                st.caption(place.addr or "주소 정보 없음")
                if st.button("판정 상세보기", key=f"detail_{place.content_id}"):
                    st.session_state.selected_place = (place.content_id, place.content_type_id)
                    st.session_state.nav = "판정 상세"
                    st.rerun()


def render():
    st.header("🔍 목적지 탐색")

    if not st.session_state.companion_indices:
        st.warning("먼저 프로필 화면에서 동반 대상을 선택해주세요.")
        return

    tab_area, tab_nearby, tab_keyword = st.tabs(["지역 선택", "내 주변", "키워드 검색"])

    with tab_area:
        content_type_id = _content_type_filter("filter_area")
        regions = api_client.ldong_code()
        region_options = [_code_and_name(r) for r in regions] if regions else []
        if not region_options:
            st.info("법정동 코드를 불러오지 못했습니다. 서비스키 설정을 확인해주세요.")
        else:
            region_code, _ = st.selectbox("시/도", region_options, format_func=lambda x: x[1], key="region_select")
            sub_regions = api_client.ldong_code(region_code) if region_code else []
            sub_options = [("", "전체")] + [_code_and_name(r) for r in sub_regions]
            signgu_code, _ = st.selectbox("시/군/구", sub_options, format_func=lambda x: x[1], key="signgu_select")
            if st.button("검색", key="search_area"):
                st.session_state.search_tab = "area"
                st.session_state.search_results = api_client.area_based_list(
                    l_dong_regn_cd=region_code,
                    l_dong_signgu_cd=signgu_code,
                    content_type_id=content_type_id,
                )
        if st.session_state.get("search_tab") == "area":
            _render_results(st.session_state.get("search_results", []))

    with tab_nearby:
        content_type_id = _content_type_filter("filter_nearby")
        col1, col2 = st.columns(2)
        with col1:
            map_x = st.number_input("경도(mapX)", value=126.9780, format="%.6f")
        with col2:
            map_y = st.number_input("위도(mapY)", value=37.5665, format="%.6f")
        radius = st.slider("반경(m)", min_value=500, max_value=20000, value=3000, step=500)
        if st.button("검색", key="search_nearby"):
            st.session_state.search_tab = "nearby"
            st.session_state.search_results = api_client.location_based_list(
                map_x=map_x, map_y=map_y, radius=radius, content_type_id=content_type_id
            )
        if st.session_state.get("search_tab") == "nearby":
            _render_results(st.session_state.get("search_results", []))

    with tab_keyword:
        content_type_id = _content_type_filter("filter_keyword")
        keyword = st.text_input("키워드", placeholder="예: 애견카페, 강아지 동반 펜션")
        if st.button("검색", key="search_keyword") and keyword:
            st.session_state.search_tab = "keyword"
            st.session_state.search_results = api_client.search_keyword(
                keyword=keyword, content_type_id=content_type_id
            )
        if st.session_state.get("search_tab") == "keyword":
            _render_results(st.session_state.get("search_results", []))

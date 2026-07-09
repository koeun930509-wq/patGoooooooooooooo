"""3) 판정 상세 화면(핵심): 배지 + 근거 + 준비물 체크리스트 + 주의사항 + 원문/상세정보 + 오판정 신고."""

import csv
import os
from datetime import datetime

import streamlit as st

from pet_guide import api_client
from pet_guide.constants import REPORTS_CSV_PATH, VERDICT_BADGES
from pet_guide.judge import judge_pet

_VERDICT_RENDER = {
    "가능": st.success,
    "조건부 가능": st.warning,
    "불가": st.error,
    "정보 부족": st.info,
}


def _report_misjudgment(pet_name: str, place_title: str, content_id: str, verdict: str, comment: str):
    os.makedirs(os.path.dirname(REPORTS_CSV_PATH), exist_ok=True)
    is_new = not os.path.exists(REPORTS_CSV_PATH)
    with open(REPORTS_CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["신고시각", "반려동물", "장소", "contentId", "판정결과", "신고내용"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), pet_name, place_title, content_id, verdict, comment])


def render():
    st.header("🧭 판정 상세")

    selected = st.session_state.get("selected_place")
    if not selected:
        st.info("탐색 화면에서 장소를 선택하면 이곳에 판정 결과가 표시됩니다.")
        return
    content_id, content_type_id = selected

    companions = [st.session_state.pets[i] for i in sorted(st.session_state.companion_indices)]
    if not companions:
        st.warning("동반 대상이 없습니다. 프로필 화면에서 선택해주세요.")
        return

    with st.spinner("장소 정보를 불러오는 중..."):
        detail = api_client.get_place_detail(content_id, content_type_id)

    if not detail.title:
        st.error("장소 정보를 불러오지 못했습니다.")
        return

    st.subheader(detail.title)

    if len(companions) > 1:
        names = [p.name for p in companions]
        chosen_name = st.selectbox("판정 대상 반려동물", names)
        pet = next(p for p in companions if p.name == chosen_name)
    else:
        pet = companions[0]
        st.caption(f"판정 대상: {pet.name}")

    result = judge_pet(pet, detail)

    badge_fn = _VERDICT_RENDER.get(result.verdict, st.info)
    badge_fn(VERDICT_BADGES.get(result.verdict, result.verdict))
    st.write(result.reason)

    if result.checklist:
        st.markdown("**✅ 필수 준비물 체크리스트**")
        for item in result.checklist:
            st.checkbox(item, key=f"checklist_{content_id}_{pet.name}_{item}")

    if result.cautions:
        st.markdown("**⚠️ 주의사항**")
        for caution in result.cautions:
            st.warning(caution)

    with st.expander("📄 원문 규정 펼쳐보기", expanded=False):
        st.write(f"- 동반유형/구역: {detail.acmpy_type_cd or '정보 없음'}")
        st.write(f"- 동반 가능 동물: {detail.acmpy_psbl_cpam or '정보 없음'}")
        st.write(f"- 동반 시 필요사항: {detail.acmpy_need_mtr or '정보 없음'}")
        st.write(f"- 기타 동반정보: {detail.etc_acmpy_info or '정보 없음'}")
        st.write(f"- 사고 대비사항: {detail.rela_acdnt_risk_mtr or '정보 없음'}")
        if result.source_quote:
            st.caption(f"판정 근거 원문: {result.source_quote}")
        st.caption(f"판정 방식: {'AI 해석' if result.source == 'llm' else '규칙 기반'}")

    with st.expander("📍 장소 기본정보", expanded=False):
        st.write(f"- 주소: {detail.addr or '정보 없음'}")
        st.write(f"- 운영시간: {detail.use_time or '정보 없음'}")
        st.write(f"- 휴무일: {detail.rest_date or '정보 없음'}")
        st.write(f"- 주차: {detail.parking or '정보 없음'}")
        st.write(f"- 전화: {detail.tel or '정보 없음'}")
        if detail.map_x and detail.map_y:
            st.iframe(
                f"https://www.google.com/maps?q={detail.map_y},{detail.map_x}&output=embed",
                height=280,
            )
        else:
            st.caption("좌표 정보가 없어 지도를 표시할 수 없습니다.")

    st.divider()
    with st.form("misjudgment_report"):
        st.markdown("**🚩 오판정 신고**")
        comment = st.text_area("실제와 다르다고 느끼신 부분을 알려주세요.", placeholder="예: 실제로는 대형견도 동반 가능했어요.")
        if st.form_submit_button("신고하기"):
            _report_misjudgment(pet.name, detail.title, content_id, result.verdict, comment)
            st.success("신고가 접수되었습니다. 감사합니다.")

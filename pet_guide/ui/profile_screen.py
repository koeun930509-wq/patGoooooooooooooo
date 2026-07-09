"""1) 프로필 화면: 반려동물 등록, 다중 관리, 이번 여행 동반 대상 선택."""

import streamlit as st

from pet_guide.constants import PET_SIZE_OPTIONS
from pet_guide.models import PetProfile


def render():
    st.header("🐾 반려동물 프로필")
    st.caption("여러 마리를 등록하고, 이번 여행에 함께할 반려동물을 선택하세요.")

    with st.form("add_pet_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름")
            species = st.selectbox("종", ["개", "고양이", "기타"])
            breed = st.text_input("견종/품종")
        with col2:
            weight_kg = st.slider("무게(kg)", min_value=0.5, max_value=90.0, value=5.0, step=0.5)
            size = st.selectbox("크기", PET_SIZE_OPTIONS)
            is_dangerous_breed = st.toggle("맹견 여부")
            can_wear_muzzle = st.toggle("입마개 착용 가능", value=True)

        with st.expander("추가 정보 (선택)"):
            vaccinated = st.checkbox("예방접종 완료")
            neutered = st.checkbox("중성화 완료")

        submitted = st.form_submit_button("반려동물 추가")
        if submitted:
            if not name:
                st.error("이름을 입력해주세요.")
            else:
                st.session_state.pets.append(
                    PetProfile(
                        name=name,
                        species=species,
                        breed=breed,
                        weight_kg=weight_kg,
                        size=size,
                        is_dangerous_breed=is_dangerous_breed,
                        can_wear_muzzle=can_wear_muzzle,
                        vaccinated=vaccinated,
                        neutered=neutered,
                    )
                )
                st.success(f"{name} 등록 완료")

    st.divider()

    if not st.session_state.pets:
        st.info("등록된 반려동물이 없습니다. 위에서 먼저 추가해주세요.")
        return

    st.subheader("등록된 반려동물 · 동반 대상 선택")
    for idx, pet in enumerate(st.session_state.pets):
        cols = st.columns([0.08, 0.72, 0.2])
        with cols[0]:
            checked = idx in st.session_state.companion_indices
            new_checked = st.checkbox(
                "동반 대상", value=checked, key=f"companion_{idx}", label_visibility="collapsed"
            )
            if new_checked:
                st.session_state.companion_indices.add(idx)
            else:
                st.session_state.companion_indices.discard(idx)
        with cols[1]:
            badge = "🐕 맹견" if pet.is_dangerous_breed else "🐕"
            st.markdown(f"**{pet.name}** ({pet.breed or pet.species}, {pet.weight_kg}kg, {pet.size}) {badge}")
        with cols[2]:
            if st.button("삭제", key=f"delete_{idx}"):
                st.session_state.pets.pop(idx)
                st.session_state.companion_indices.discard(idx)
                st.rerun()

    if not st.session_state.companion_indices:
        st.warning("동반 대상을 최소 1마리 선택해야 탐색/판정을 진행할 수 있습니다.")

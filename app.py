"""PetGo — 반려동물 동반 여행 가이드 MVP 엔트리포인트."""

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from pet_guide.ui import detail_screen, explore_screen, profile_screen

st.set_page_config(page_title="PetGo · 반려동물 동반 여행 가이드", page_icon="puppyCat.png", layout="centered")

_DEFAULTS = {
    "pets": [],
    "companion_indices": set(),
    "search_results": [],
    "search_tab": None,
    "selected_place": None,
    "nav": "프로필",
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown(
    "<style>.block-container { padding-top: 2rem; }</style>",
    unsafe_allow_html=True,
)
st.markdown("<h1 style='text-align: center; margin-top: 0;'>🐾 PetGo</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: gray;'>반려동물 특성과 장소 규정을 대조해 헛걸음을 없애는 여행 가이드</p>",
    unsafe_allow_html=True,
)

_, banner_col, _ = st.columns([1, 3, 1])
with banner_col:
    st.image("puppyCat.png", width="stretch")

_STEPS = [("프로필", "①"), ("탐색", "②"), ("판정 상세", "③")]
step_cols = st.columns([3, 1, 3, 1, 3], vertical_alignment="center")
for i, (step, icon) in enumerate(_STEPS):
    with step_cols[i * 2]:
        if st.button(
            f"{icon} {step}",
            key=f"nav_step_{step}",
            type="primary" if st.session_state.nav == step else "secondary",
            width="stretch",
        ):
            st.session_state.nav = step
            st.rerun()
    if i < len(_STEPS) - 1:
        with step_cols[i * 2 + 1]:
            st.markdown("<div style='text-align: center;'>→</div>", unsafe_allow_html=True)

nav = st.session_state.nav
_STEP_NAMES = [s for s, _ in _STEPS]
current_idx = _STEP_NAMES.index(nav)

if nav == "프로필":
    profile_screen.render()
elif nav == "탐색":
    explore_screen.render()
elif nav == "판정 상세":
    detail_screen.render()

st.divider()
prev_col, _, next_col = st.columns([1, 2, 1])
with prev_col:
    if current_idx > 0 and st.button("← 이전", key="btn_prev", width="stretch"):
        st.session_state.nav = _STEP_NAMES[current_idx - 1]
        st.rerun()
with next_col:
    # "탐색" 화면은 결과 카드의 "판정 상세보기" 버튼으로 이미 다음 단계로 넘어갈 수 있으므로 생략한다.
    if nav == "프로필" and st.button("다음 →", key="btn_next", width="stretch"):
        st.session_state.nav = _STEP_NAMES[current_idx + 1]
        st.rerun()

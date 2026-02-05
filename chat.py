import streamlit as st
import uuid, os
from datetime import datetime
from collections import namedtuple
from src.rag import rag_answer
from src.chroma_db import extract_text_from_pdf, add_document

# --- 데이터 정의 ---
Targets = namedtuple('Targets', ['temp_min', 'temp_max', 'hum_min', 'hum_max', 'co2_min', 'co2_max', 'light_min', 'light_max'])
GREENBIOCHAT = {
    "채팅 모드": {"welcome": "안녕하세요! 스마트 온실 관리 챗봇입니다."},
    "1번 온실": {"targets": Targets(20, 26, 55, 75, 600, 1200, 8000, 25000), "snapshot": {"temp_c": 24.3, "humidity": 68.0, "light_lux": 12000, "co2_ppm": 980}},
    "2번 온실": {"targets": Targets(18, 24, 60, 85, 700, 1400, 6000, 22000), "snapshot": {"temp_c": 26.8, "humidity": 52.0, "light_lux": 16000, "co2_ppm": 1550}}
}

def init_chat(mode):
    cid = str(uuid.uuid4())[:8]
    msg = GREENBIOCHAT[mode].get("welcome") or get_analysis_message(mode, GREENBIOCHAT[mode])
    st.session_state.chat_sessions[mode][cid] = {"title": "", "messages": [{"role": "assistant", "content": msg}], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    st.session_state.active_chat_id[mode] = cid
    return cid

def get_analysis_message(name, data):
    s, t = data['snapshot'], data['targets']
    res = [f"{k}({s[v]}{u})" for k, v, u, mi, ma in [("온도", "temp_c", "°C", t.temp_min, t.temp_max), ("습도", "humidity", "%", t.hum_min, t.hum_max)] if not (mi <= s[v] <= ma)]
    return f"**{name}** 상태: {'정상' if not res else '주의(' + ' / '.join(res) + ')'}\n\n무엇을 도와드릴까요?"

def chat_page(cookies=None):
    st.session_state.setdefault("current_mode", "채팅 모드")
    st.session_state.setdefault("chat_sessions", {k: {} for k in GREENBIOCHAT})
    st.session_state.setdefault("active_chat_id", {k: None for k in GREENBIOCHAT})
    st.session_state.setdefault("is_generating", False)

    # --- CSS: 사이드바 위에서도 글씨가 보이도록 설정 ---
    username = st.session_state.get("user_info", {}).get("username", "User")
    user_initial = username[0].upper() if username else "U"

    st.markdown(f"""
        <style>
        /* 기본 레이아웃 */
        [data-testid="stSidebarNav"], [data-testid="stStatusWidget"], [data-testid="stSpinner"], .stSpinner, [data-testid="stAppViewBlockContainer"] > div:first-child > div[data-testid="stVerticalBlock"] > div:first-child iframe {{ display: none !important; }}
        header {{ background-color: #3D4936 !important; z-index: 999 !important; }}
        .stApp {{ background-color: #F8F9F2; }}
        
        /* 사이드바 내부 스타일 */
        [data-testid="stSidebar"] {{ background-color: #3D4936 !important; z-index: 10000 !important; }}
        [data-testid="stSidebar"] button p {{ color: black !important; font-weight: 600; }}

        /* ★ 좌측 상단 로고: 사이드바보다 높은 z-index 부여 ★ */
        #header-logo {{ 
            position: fixed; 
            top: 15px; 
            left: 20px; 
            z-index: 100001 !important; /* 사이드바(10000)보다 위에 위치 */
            font-weight: 800; 
            font-size: 24px; 
            color: white !important;
            letter-spacing: -0.5px;
            pointer-events: none; /* 클릭 간섭 방지 */
        }}
        
        /* ★ 우측 상단 프로필 ★ */
        .fixed-profile-container {{
            position: fixed;
            top: 10px;
            right: 20px;
            z-index: 100002 !important; /* 로고보다도 위에 위치 */
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}
        
        .profile-circle {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background-color: #8B9D7C;
            border: 2px solid white;
            color: white !important;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        #profile-checkbox {{ display: none; }}
        .profile-dropdown {{
            display: none;
            margin-top: 8px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            min-width: 120px;
            overflow: hidden;
        }}
        #profile-checkbox:checked ~ .profile-dropdown {{ display: block; }}
        
        .dropdown-item {{
            padding: 12px 16px;
            color: #333 !important;
            text-decoration: none !important;
            display: block;
            font-size: 14px;
        }}
        .dropdown-item:hover {{ background-color: #f8f9fa; color: red !important; }}
        
        /* 채팅 입력창 레이아웃 */
        div[data-testid="stChatInput"] {{
            position: fixed;
            bottom: 30px !important;
            width: 55% !important;
            left: 20% !important;
            z-index: 998;
        }}
        </style>

        <div id="header-logo">GREENBIOCHAT</div>
        
        <div class="fixed-profile-container">
            <input type="checkbox" id="profile-checkbox">
            <label for="profile-checkbox" class="profile-circle">{user_initial}</label>
            <div class="profile-dropdown">
                <div style="padding: 10px 16px; font-size: 11px; color: #888; background: #fafafa;">{username}님</div>
                <a href="?logout=1" class="dropdown-item" style="color: red !important;">로그아웃</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 사이드바 내용 ---
    with st.sidebar:
        # 로고와 버튼이 겹치지 않게 상단 여백 확보
        st.markdown("<div style='margin-top: 60px;'></div>", unsafe_allow_html=True)
        for m in GREENBIOCHAT.keys():
            if st.button(m, key=f"btn_{m}", type="primary" if st.session_state.current_mode == m else "secondary", use_container_width=True):
                st.session_state.current_mode = m
                if not st.session_state.active_chat_id[m]: init_chat(m)
                st.rerun()

    col_main, col_right = st.columns([0.72, 0.28], gap="medium")
    mode = st.session_state.current_mode
    
    with col_main:
        if mode != "채팅 모드":
            st.subheader(f"{mode} 모니터링")
            data = GREENBIOCHAT[mode]['snapshot']
            m_cols = st.columns(4)
            for col, (l, v) in zip(m_cols, [("온도", f"{data['temp_c']}°C"), ("습도", f"{data['humidity']}%"), ("CO2", f"{data['co2_ppm']}ppm"), ("조도", f"{data['light_lux']}Lux")]):
                col.metric(l, v)
        
        cid = st.session_state.active_chat_id[mode] or init_chat(mode)
        session = st.session_state.chat_sessions[mode][cid]
        
        for msg in session["messages"]:
            st.chat_message(msg["role"]).write(msg["content"])

        # 채팅바 (CSS에서 너비와 위치를 제어함)
        if prompt := st.chat_input("메시지를 입력하세요..."):
            if not session["title"]: session["title"] = prompt[:15] + "..."
            session["messages"].append({"role": "user", "content": prompt})
            st.session_state.is_generating = True
            st.rerun()

        if st.session_state.is_generating:
            with st.spinner("생성 중..."):
                try:
                    ans = rag_answer(session["messages"][-1]["content"])["answer"]
                    session["messages"].append({"role": "assistant", "content": ans})
                except Exception as e: st.error(f"오류: {e}")
            st.session_state.is_generating = False
            st.rerun()

    with col_right:
        with st.container(border=True):
            st.write("### 대화 기록")
            for sid, c in sorted(st.session_state.chat_sessions[mode].items(), key=lambda x: x[1]['created_at'], reverse=True):
                if st.button(c['title'] or "새 대화", key=f"sid_{sid}", use_container_width=True):
                    st.session_state.active_chat_id[mode] = sid
                    st.rerun()
            if st.button("+ 새 채팅", use_container_width=True, key="new_chat_btn"):
                init_chat(mode); st.rerun()
        
        with st.container(border=True):
            st.write("### 문서 업로드")
            files = st.file_uploader("UP", type='pdf', accept_multiple_files=True, label_visibility="collapsed")
            if files:
                for f in files:
                    os.makedirs("datafile", exist_ok=True)
                    path = os.path.join("datafile", f.name)
                    with open(path, "wb") as tmp: tmp.write(f.read())
                    txt = extract_text_from_pdf(path)
                    if txt: add_document(f.name, txt); st.toast(f"{f.name} 완료")
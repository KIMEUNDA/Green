import streamlit as st
import uuid, os, requests, json, pymysql
from datetime import datetime
from collections import namedtuple
from src.rag import rag_answer
from src.chroma_db import extract_text_from_pdf, add_document


# DB 연결 및 저장/삭제 함수
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',          
        password='1234',      # 회원정보와 동일한 비밀번호
        db='test',            # 회원정보가 있는 test 서랍장
        charset='utf8mb4'
    )

def save_chat_to_db(session_id, username, mode, title, messages, created_at):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 이미 있는 채팅방이면 내용만 업데이트(UPDATE), 새 채팅방이면 새로 생성(INSERT)
        sql = """
            INSERT INTO chat_history (session_id, username, mode, title, messages, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE title=%s, messages=%s
        """
        msg_json = json.dumps(messages, ensure_ascii=False)
        cursor.execute(sql, (session_id, username, mode, title, msg_json, created_at, title, msg_json))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB 저장 에러: {e}")

def delete_chat_from_db(session_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE session_id = %s", (session_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB 삭제 에러: {e}")
# ==========================================

# --- 데이터 정의 ---
Targets = namedtuple('Targets', ['temp_min', 'temp_max', 'hum_min', 'hum_max', 'co2_min', 'co2_max', 'light_min', 'light_max'])
GREENBIOCHAT = {
    "채팅 모드": {"welcome": "안녕하세요! 스마트 온실 관리 챗봇입니다."},
    "1번 온실": {"targets": Targets(20, 26, 55, 75, 600, 1200, 8000, 25000), "snapshot": {"temp_c": 24.3, "humidity": 68.0, "light_lux": 12000, "co2_ppm": 980}},
    "2번 온실": {"targets": Targets(18, 24, 60, 85, 700, 1400, 6000, 22000), "snapshot": {"temp_c": 26.8, "humidity": 52.0, "light_lux": 16000, "co2_ppm": 1550}}
}

# 순천시 실시간 날씨 정보를 가져오는 함수
@st.cache_data(ttl=3600)
def get_suncheon_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=34.9506&longitude=127.4872&current=temperature_2m,relative_humidity_2m"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            temp = data["current"]["temperature_2m"]
            hum = data["current"]["relative_humidity_2m"]
            return temp, hum
    except Exception as e:
        print(f"날씨 정보 로드 실패: {e}")
    return 18.5, 42 

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
    
    username = st.session_state.get("user_info", {}).get("username", "User")
    user_initial = username[0].upper() if username else "U"

    st.markdown(f"""
        <style>
        [data-testid="stSidebarNav"], [data-testid="stStatusWidget"], [data-testid="stSpinner"], .stSpinner, [data-testid="stAppViewBlockContainer"] > div:first-child > div[data-testid="stVerticalBlock"] > div:first-child iframe {{ display: none !important; }}
        header {{ background-color: #3D4936 !important; z-index: 999 !important; }}
        .stApp {{ background-color: #F8F9F2; }}
        .block-container {{ padding-bottom: 50px !important; }}
        [data-testid="stSidebar"] {{ background-color: #3D4936 !important; z-index: 10000 !important; }}
        [data-testid="stSidebar"] button p {{ color: black !important; font-weight: 600; }}

        #header-logo {{ position: fixed; top: 15px; left: 20px; z-index: 100001 !important; font-weight: 800; font-size: 24px; color: white !important; letter-spacing: -0.5px; pointer-events: none; }}
        .fixed-profile-container {{ position: fixed; top: 10px; right: 20px; z-index: 100002 !important; display: flex; flex-direction: column; align-items: flex-end; }}
        .profile-circle {{ width: 38px; height: 38px; border-radius: 50%; background-color: #8B9D7C; border: 2px solid white; color: white !important; display: flex; align-items: center; justify-content: center; font-weight: bold; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }}
        
        #profile-checkbox {{ display: none; }}
        .profile-dropdown {{ display: none; margin-top: 8px; background-color: white; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); min-width: 120px; overflow: hidden; }}
        #profile-checkbox:checked ~ .profile-dropdown {{ display: block; }}
        .dropdown-item {{ padding: 12px 16px; color: #333 !important; text-decoration: none !important; display: block; font-size: 14px; }}
        .dropdown-item:hover {{ background-color: #f8f9fa; color: #6A994E !important; }}
        
        div[data-testid="stChatInput"] {{ position: fixed; bottom: 30px !important; width: 55% !important; left: 20% !important; z-index: 998; }}

        .floating-help-btn {{ position: fixed; bottom: 40px; right: 40px; width: 55px; height: 55px; background-color: #6A994E; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; z-index: 99999; transition: all 0.3s ease; }}
        .floating-help-btn:hover {{ transform: translateY(-5px); box-shadow: 0 6px 16px rgba(0,0,0,0.2); }}
        .help-content {{ display: none; position: absolute; bottom: 70px; right: 0; width: 340px; background-color: white; color: #1A2017; padding: 24px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); font-size: 14px; line-height: 1.6; text-align: left; border: 1px solid #EAECE4; cursor: default; }}
        .floating-help-btn:hover .help-content {{ display: block; animation: fadeIn 0.3s; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>

        <div id="header-logo">GREENBIOCHAT</div>
        
        <div class="fixed-profile-container">
            <input type="checkbox" id="profile-checkbox">
            <label for="profile-checkbox" class="profile-circle">{user_initial}</label>
            <div class="profile-dropdown">
                <div style="padding: 10px 16px; font-size: 11px; color: #888; background: #fafafa;">{username}님</div>
                <a href="?logout=1" target="_top" class="dropdown-item" style="color: #6A994E !important;">로그아웃</a>
            </div>
        </div>

        <div class="floating-help-btn">
            ?
            <div class="help-content">
                <div style="font-size:16px; font-weight:bold; margin-bottom:12px; color:#6A994E;">🌿 GREENBIO 챗봇 이용 가이드</div>
                • <b>채팅 모드:</b> 스마트팜, 작물 생육 등에 관한 일반적인 대화 및 전문 질문이 가능합니다.<br><br>
                • <b>온실 모니터링:</b> 좌측 버튼을 눌러 각 온실의 실시간 상태(온도, 습도 등)를 확인하세요.<br><br>
                • <b>문서 업로드(RAG):</b> PDF 문서를 우측 상단에 올리고 질문하면, 해당 문서의 내용을 바탕으로 정확하게 답변해 줍니다.<br><br>
                <b>챗봇 오류 문의:</b> 010-*947-895*
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div style='margin-top: 60px;'></div>", unsafe_allow_html=True)
        
        for m in GREENBIOCHAT.keys():
            if st.button(m, key=f"btn_{m}", type="primary" if st.session_state.current_mode == m else "secondary", use_container_width=True):
                st.session_state.current_mode = m
                if not st.session_state.active_chat_id[m]: init_chat(m)
                st.rerun()

        st.markdown("<hr style='margin: 30px 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)

        st.markdown("<p style='color: white; font-weight: bold; margin-bottom: 5px;'>🌤️ 현장 외부 기상 (순천시)</p>", unsafe_allow_html=True)
        
        current_temp, current_hum = get_suncheon_weather()
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            col1.markdown(f"<div style='text-align: center;'><span style='font-size: 12px; color: #888;'>기온</span><br><span style='font-size: 20px; font-weight: bold; color: #1A2017;'>{current_temp}°C</span></div>", unsafe_allow_html=True)
            col2.markdown(f"<div style='text-align: center;'><span style='font-size: 12px; color: #888;'>습도</span><br><span style='font-size: 20px; font-weight: bold; color: #1A2017;'>{current_hum}%</span></div>", unsafe_allow_html=True)

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

        if len(session["messages"]) == 1:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            quick_prompts = [
                "이 챗봇에 대해 알려줘",
                "스마트 온실이 좋은 점은?", 
                "업로드한 문서 핵심 요약해 줘"
            ]
            
            cols = st.columns(3)
            for i, prompt_text in enumerate(quick_prompts):
                if cols[i].button(prompt_text, key=f"quick_{mode}_{i}", use_container_width=True):
                    if not session["title"]: 
                        session["title"] = prompt_text[:15] + "..."
                    session["messages"].append({"role": "user", "content": prompt_text})
                    
                    # 추천 질문을 클릭했을 때 DB에 내역 저장
                    save_chat_to_db(cid, username, mode, session["title"], session["messages"], session["created_at"])
                    
                    st.session_state.is_generating = True
                    st.rerun()

        if st.session_state.is_generating:
            with st.spinner("생성 중..."):
                try:
                    ans = rag_answer(session["messages"])["answer"]
                    session["messages"].append({"role": "assistant", "content": ans})
                    
                    # 챗봇이 답변을 완료하면 DB에 최종 내역 업데이트
                    save_chat_to_db(cid, username, mode, session["title"], session["messages"], session["created_at"])
                    
                except Exception as e: 
                    st.error(f"오류: {e}")
                    print(f"\n[에러 상세]: {e}\n") 
                    st.stop() 

            st.session_state.is_generating = False
            st.rerun()

        st.markdown("<div style='height: 150px; display: block; clear: both;'></div>", unsafe_allow_html=True)

    with col_right:
        with st.container(border=True):
            st.write("### 대화 기록")
            for sid, c in sorted(st.session_state.chat_sessions[mode].items(), key=lambda x: x[1]['created_at'], reverse=True):
                
                col_btn, col_del = st.columns([0.85, 0.15])
                
                with col_btn:
                    if st.button(c['title'] or "새 대화", key=f"sid_{sid}", use_container_width=True):
                        st.session_state.active_chat_id[mode] = sid
                        st.rerun()
                
                with col_del:
                    if st.button("X", key=f"del_{sid}", use_container_width=True):
                        # X 버튼을 누르면 DB에서도 대화 기록 완전히 삭제
                        delete_chat_from_db(sid)
                        
                        del st.session_state.chat_sessions[mode][sid]
                        if st.session_state.active_chat_id[mode] == sid:
                            st.session_state.active_chat_id[mode] = None
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

    if prompt := st.chat_input("메시지를 입력하세요..."):
        if not session["title"]: session["title"] = prompt[:15] + "..."
        session["messages"].append({"role": "user", "content": prompt})
        
        # 사용자가 채팅창에 엔터를 쳤을 때 우선적으로 DB에 저장
        save_chat_to_db(cid, username, mode, session["title"], session["messages"], session["created_at"])
        
        st.session_state.is_generating = True
        st.rerun()

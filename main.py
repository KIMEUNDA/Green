import streamlit as st
import json
from streamlit_cookies import CookieManager
from login import login_page
from chat import chat_page

st.set_page_config(layout="wide", page_title="GreenBio Chatbot")

# --- 쿠키 매니저 초기화 ---
cookies = CookieManager()
cookie_val = cookies.get('greenbio_login')

# --- 세션 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# 1. URL에서 로그아웃 신호 감지
is_logging_out = st.query_params.get("logout") == "1"

# --- 로그아웃 처리 ---
if is_logging_out:
    # 세션 변수 명시적 해제
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = None
    
    # 쿠키 삭제 명령 (이제 rerun이 없으므로 브라우저에 무사히 도착함)
    cookies.delete('greenbio_login')
    
    # URL 파라미터 깔끔하게 지우기
    st.query_params.clear()

# --- 쿠키에서 로그인 복원 ---
# 2. 방어막: 로그아웃 중이 아닐 때만(and not is_logging_out) 쿠키를 읽어 자동 로그인
if not st.session_state['logged_in'] and not is_logging_out:
    if cookie_val:
        try:
            data = json.loads(cookie_val) if isinstance(cookie_val, str) else cookie_val
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = {
                'username': data['username'],
                'role': data['role']
            }
        except:
            cookies.delete('greenbio_login')

# --- 페이지 라우팅 ---
if st.session_state.get('logged_in'):
    chat_page(cookies=cookies)
else:
    login_page(cookies=cookies)
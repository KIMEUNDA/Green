import streamlit as st
import json
from streamlit_cookies import CookieManager
from login import login_page
from chat import chat_page

st.set_page_config(layout="wide", page_title="GreenBio Chatbot")

# --- 쿠키 매니저 초기화 ---
cookies = CookieManager()
cookies.get('greenbio_login')  # 쿠키 읽기 트리거

# --- 세션 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# --- 쿠키에서 로그인 복원 ---
if not st.session_state['logged_in']:
    cookie_val = cookies.get('greenbio_login')
    if cookie_val:
        try:
            # CookieManager가 자동 파싱하여 dict를 반환할 수 있음
            data = json.loads(cookie_val) if isinstance(cookie_val, str) else cookie_val
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = {
                'username': data['username'],
                'role': data['role']
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            cookies.delete('greenbio_login')

# --- 로그아웃 처리 ---
if st.query_params.get("logout") == "1":
    cookies.delete('greenbio_login')
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# --- 페이지 라우팅 ---
if st.session_state.get('logged_in'):
    chat_page(cookies=cookies)
else:
    login_page(cookies=cookies)

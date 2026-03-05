import streamlit as st
import time
import extra_streamlit_components as stx  
from login import login_page
from chat import chat_page

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="GreenBio Chatbot")

# 쿠키 매니저 실행
cookie_manager = stx.CookieManager(key="main_cookie")

# URL에 '?logout=1' 신호가 들어왔는지 확인 (로그아웃 버튼 클릭 시)
if "logout" in st.query_params:
    # 쿠키 삭제 시 에러가 나면 부드럽게 무시하고 넘어가도록 예외 처리 추가!
    try:
        cookie_manager.delete("user_id") 
    except KeyError:
        pass # 이미 쿠키가 없으면 그냥 조용히 넘어감
        
    st.session_state.clear()         # 임시 메모리(세션) 싹 비우기
    time.sleep(0.5)                  # 확실히 지워질 때까지 대기
    st.query_params.clear()          # URL에 남아있는 '?logout=1' 글자 지우기
    st.rerun()                       # 화면을 새로고침하여 로그인 화면으로 이동

# 로그인 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# 화면 분기 처리
if not st.session_state['logged_in']:
    login_page()
else:
    chat_page()

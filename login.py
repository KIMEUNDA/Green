import streamlit as st
import json
import time
import re
import pymysql
import extra_streamlit_components as stx  
from src.auth import create_user, get_user, verify_password

def get_db_connection():
    # 본인의 MariaDB 정보에 맞게 수정해 주세요!
    return pymysql.connect(
        host='localhost',
        user='root',          # DB 아이디
        password='1234',      # DB 비밀번호
        db='test',     # 방금 만든 데이터베이스 이름
        charset='utf8mb4'
    )

def load_user_chat_history(username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM chat_history WHERE username = %s ORDER BY created_at DESC", (username,))
        rows = cursor.fetchall()
        conn.close()
        
        history = {
            "채팅 모드": {},
            "1번 온실": {},
            "2번 온실": {}
        }
        
        for row in rows:
            mode = row['mode']
            msgs = json.loads(row['messages']) if isinstance(row['messages'], str) else row['messages']
            
            if mode in history:
                history[mode][row['session_id']] = {
                    "title": row['title'],
                    "messages": msgs,
                    "created_at": str(row['created_at'])
                }
        return history
    except Exception as e:
        print(f"대화 기록 불러오기 에러: {e}")
        return None

def login_page():
    # 캐시 함수를 없애고 직접 쿠키 매니저 실행 (노란 경고창 해결)
    cookie_manager = stx.CookieManager(key="login_cookie")
    
    # 이미 로그인된 쿠키(티켓)가 있는지 검사해서 자동 로그인 처리
    cookie_user_id = cookie_manager.get(cookie="user_id")
    
    if cookie_user_id and not st.session_state.get('logged_in'):
        user = get_user(cookie_user_id)
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = {
                "username": user[1],
                "role": user[4]
            }
            db_chat_history = load_user_chat_history(user[1])
            if db_chat_history:
                st.session_state['chat_sessions'] = db_chat_history
            time.sleep(0.1)
            st.rerun()

    # 아래는 화면 UI 구성
    with st.sidebar:
        st.title("Access Control")
        st.info("로그인 후 사용 가능")
        st.write("---")
        st.caption("Green Bio Project © 2026")

    empty1, col, empty2 = st.columns([1, 0.8, 1])

    with col:
        st.markdown("## 환영합니다!")
        st.write("Green Bio 챗봇입니다.")
        st.write("") 

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        with tab1:
            with st.container(border=True):
                with st.form(key="login_form"):
                    user_id = st.text_input("이메일", placeholder="이메일을 입력하세요")
                    user_pw = st.text_input("비밀번호", type="password", placeholder="Password")

                    st.write("") 
                    login_submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
                
                if login_submitted:
                    if not user_id or not user_pw:
                        st.warning("이메일과 비밀번호를 모두 입력해주세요.")
                    else:
                        user = get_user(user_id)
                        
                        if user:
                            db_password_hash = user[3] 
                            db_role = user[4]

                            if verify_password(user_pw, db_password_hash):
                                # 로그인 성공 시 브라우저에 쿠키(티켓) 발급
                                cookie_manager.set("user_id", user_id, max_age=86400)
                                
                                st.session_state['logged_in'] = True
                                st.session_state['user_info'] = {
                                    "username": user[1],
                                    "role": db_role
                                }
                                
                                db_chat_history = load_user_chat_history(user[1])
                                if db_chat_history:
                                    st.session_state['chat_sessions'] = db_chat_history

                                st.success(f"{user[1]}님 환영합니다!")
                                time.sleep(0.5) 
                                st.rerun()
                            else:
                                st.error("비밀번호가 일치하지 않습니다.")
                        else:
                            st.error("존재하지 않는 이메일입니다.")

        with tab2:
            with st.container(border=True):
                st.info("회원가입")
                
                with st.form(key="signup_form"):
                    new_name = st.text_input("이름")
                    new_email = st.text_input("이메일")
                    new_pw = st.text_input("비밀번호 (Password)", type="password")
                    new_pw_check = st.text_input("비밀번호 확인", type="password")
                    
                    st.write("")
                    signup_submitted = st.form_submit_button("가입하기", use_container_width=True)
                
                if signup_submitted:
                    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if not (new_name and new_email and new_pw and new_pw_check):
                        st.warning("모든 정보를 입력해주세요.")
                        
                    elif not re.match(email_pattern, new_email):
                        st.warning("유효하지 않은 이메일 형식입니다. (예: user@example.com)")

                    elif new_pw != new_pw_check:
                        st.error("비밀번호가 일치하지 않습니다. 다시 확인해주세요.")
                        
                    else:
                        if create_user(new_name, new_email, new_pw, role='user'):
                            st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해주세요.")
                        else:
                            st.error("가입 실패: 이미 존재하는 아이디거나 이메일입니다.")

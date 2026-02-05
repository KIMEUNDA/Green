import streamlit as st
import json
import time
import re
from src.auth import create_user, get_user, verify_password


def login_page(cookies=None):
    with st.sidebar:
        st.title("Greenbio Chat")
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

                user_id = st.text_input("이메일", placeholder="이메일을 입력하세요", key="login_email")
                user_pw = st.text_input("비밀번호", type="password", placeholder="Password", key="login_pw")

                st.write("")
                if st.button("로그인", type="primary", use_container_width=True):
                    if not user_id or not user_pw:
                        st.warning("이메일과 비밀번호를 모두 입력해주세요.")
                    else:
                        user = get_user(user_id)

                        if user:
                            db_password_hash = user[3]
                            db_role = user[4]

                            if verify_password(user_pw, db_password_hash):
                                st.session_state['logged_in'] = True
                                st.session_state['user_info'] = {
                                    "username": user[1],
                                    "role": db_role
                                }
                                st.success(f"{user[1]}님 환영합니다!")
                                if cookies is not None:
                                    cookies.set('greenbio_login', json.dumps({
                                        'username': user[1],
                                        'role': db_role
                                    }), options={'path': '/'})
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("비밀번호가 일치하지 않습니다.")
                        else:
                            st.error("존재하지 않는 이메일입니다.")

        with tab2:
            with st.container(border=True):
                st.info("회원가입")
                new_name = st.text_input("이름", placeholder="이름을 입력하세요", key="reg_name")
                new_email = st.text_input("이메일", placeholder="이메일을 입력하세요", key="reg_email")
                new_pw = st.text_input("비밀번호 (Password)", type="password", placeholder="비밀번호를 입력하세요", key="reg_pw")
                new_pw_check = st.text_input("비밀번호 확인", type="password", placeholder="한 번 더 입력하세요", key="reg_pw_check")

                st.write("")
                if st.button("가입하기", use_container_width=True):
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

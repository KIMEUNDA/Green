import streamlit as st
import json
from streamlit_cookies import CookieManager
from login import login_page
from chat import chat_page

st.set_page_config(layout="wide", page_title="GreenBio Chatbot")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

if not st.session_state['logged_in']:
    login_page()
else:
    chat_page()

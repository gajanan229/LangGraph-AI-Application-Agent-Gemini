import streamlit as st
import threading
import os
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from playwright.sync_api import sync_playwright
import time
from scrape import start_scraper

load_dotenv()

st.title('Job Scraper Test Interface')

if 'running' not in st.session_state:
    st.session_state.running = False
    st.session_state.waiting_2fa = False
    st.session_state['2fa_code'] = None
    st.session_state.status = ''

if not st.session_state.running:
    if st.button('Test Scraper'):
        st.session_state.running = True
        thread = threading.Thread(target=start_scraper)
        add_script_run_ctx(thread, get_script_run_ctx())
        thread.start()
else:
    st.write(st.session_state.status)

if st.session_state.waiting_2fa:
    code = st.text_input('Enter Verification Code:')
    if st.button('Submit 2FA'):
        st.session_state['2fa_code'] = code 
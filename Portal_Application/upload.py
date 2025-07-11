import re
from playwright.sync_api import Page, expect
import os
import dotenv
import streamlit as st
from playwright.sync_api import sync_playwright
import time
import asyncio

dotenv.load_dotenv()

TMU_USERNAME = os.getenv("TMU_USERNAME")
TMU_PASSWORD = os.getenv("TMU_PASSWORD")
url = os.getenv("url")

def start_uploader():
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    TMU_USERNAME = os.getenv('TMU_USERNAME')
    TMU_PASSWORD = os.getenv('TMU_PASSWORD')
    url = os.getenv('url')
    st.session_state.status = 'Launching browser...'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        st.session_state.status = 'Navigating to login...'
        page.goto(url)
        page.get_by_role("textbox", name="torontomu username").fill(TMU_USERNAME)
        page.get_by_role("textbox", name="Password").fill(TMU_PASSWORD)
        page.get_by_role("button", name="Log in").click()
        st.session_state.status = 'Waiting for 2FA page...'
        page.get_by_role("textbox", name="Verification Code:").wait_for(state='visible', timeout=60000) # Reverted to more robust locator and increased timeout
        st.session_state.waiting_2fa = True
        st.rerun()  # Trigger rerun to show prompt
        st.session_state.status = 'Waiting for 2FA code...'
        while st.session_state.get('2fa_code') is None:
            time.sleep(0.5)
        code = st.session_state['2fa_code']
        st.session_state['2fa_code'] = None
        st.session_state.waiting_2fa = False
        page.get_by_role("textbox", name="Verification Code:").fill(code)
        page.get_by_role("button", name="Log in").click()
        st.session_state.status = 'Navigating to documents...'
        page.get_by_role("link", name="Coop").click()
        page.get_by_role("link", name="Documents").first.click()
        page.locator("a").filter(has_text="Upload Document").click()
        page.get_by_role("textbox", name="Name").click()
        page.get_by_role("textbox", name="Name").fill("resume_test")
        page.get_by_label("Type").select_option("2")
        page.get_by_text("Choose File").click()
        page.locator("body").set_input_files("Gajanan_Vig_Resume_AI.pdf")
        page.get_by_role("link", name="Upload Document").click()
        st.session_state.status = 'Resume uploaded. Uploading cover letter...'
        page.locator("a").filter(has_text="Upload Document").click()
        page.get_by_role("textbox", name="Name").click()
        page.get_by_role("textbox", name="Name").fill("cover letter_test")
        page.get_by_label("Type").select_option("1")
        page.get_by_text("Choose File").click()
        page.locator("body").set_input_files("Gajanan_Vig_CL_AI.pdf")
        page.get_by_role("link", name="Upload Document").click()
        st.session_state.status = 'Uploads complete.'
        time.sleep(60)  # Keep browser open for inspection
        browser.close()
        st.session_state.running = False
        st.rerun() 
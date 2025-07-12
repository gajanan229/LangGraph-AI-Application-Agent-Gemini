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
TMU_PASSWORD = os.getenv("password")
url = os.getenv("url")
file_path = os.getenv("INPUT_FILES")

def start_uploader():
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    TMU_USERNAME = os.getenv('TMU_USERNAME')
    TMU_PASSWORD = os.getenv('password')
    url = os.getenv('url')
    file_path = os.getenv('file_path')
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
        time.sleep(1)
        page.locator('input[type="file"]').set_input_files(file_path)
        time.sleep(3)
        page.locator('#submitFileUploadFormBtn').click()
        st.session_state.status = 'Resume uploaded. Uploading cover letter...'
        time.sleep(3)
        page.locator('a.btn.btn-primary.btn-small', has_text='Upload Document').click()
        page.get_by_role("textbox", name="Name").click()
        page.get_by_role("textbox", name="Name").fill("cover letter_test")
        page.get_by_label("Type").select_option("1")
        time.sleep(1)
        page.locator('input[type="file"]').set_input_files(file_path)
        time.sleep(3)
        page.locator('#submitFileUploadFormBtn').click()
        st.session_state.status = 'Uploads complete.'
        st.session_state.status = 'Navigating to Shortlist...'
        page.get_by_role("link", name="Job Postings").first.click()
        page.get_by_role("link", name="Shortlist").click() 
        page.wait_for_selector('#postingsTable', state='visible', timeout=30000)
        time.sleep(1)
        rows = page.locator('#postingsTable tbody tr')
        for i in range(rows.count()):
            row = rows.nth(i)
            first_td = row.locator('td:first-child').inner_text().strip()
            if first_td != '':
                job_id_td = row.locator('td:nth-child(4)')
                job_id = job_id_td.inner_text().strip()
                if job_id == '96386':
                    with page.expect_popup() as page1_info:
                        row.locator('a:has-text("Apply")').click()
                    page1 = page1_info.value
                    page1.bring_to_front()
                    st.session_state.status = 'Applying to job...'
                    time.sleep(2) 
                    page1.locator('button.applyButton').click() 
                    page1.get_by_role("radio", name="CREATE A CUSTOMIZED").check()
                    page1.get_by_role("textbox", name="Package Name * :").fill("Application for 96386")
                    time.sleep(1)
                    # Use regex to match "Cover Letter * :" or "Cover Letter  :"
                    cover_select = page1.get_by_label(re.compile(r"Cover Letter\s*\*? :"))
                    options = cover_select.locator('option').all()
                    for opt in options:
                        if 'cover letter_test' in opt.inner_text():
                            cover_select.select_option(opt.get_attribute('value'))
                            break
                    resume_select = page1.get_by_label(re.compile(r"Resume\s*\*? :"))
                    options = resume_select.locator('option').all()
                    for opt in options:
                        if 'resume_test' in opt.inner_text():
                            resume_select.select_option(opt.get_attribute('value'))
                            break
                    transcript_select = page1.get_by_label(re.compile(r"Transcript\s*\*? :"))
                    options = transcript_select.locator('option').all()
                    for opt in options:
                        if 'W2025' in opt.inner_text():
                            transcript_select.select_option(opt.get_attribute('value'))
                            break
                    time.sleep(10)
                    page1.get_by_role("button", name="Submit Application").click()
                    st.session_state.status = 'Application submitted.'
                    break 
        time.sleep(60)  # Keep browser open for inspection
        browser.close() 
        st.session_state.running = False
        st.rerun()    
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


def start_scraper():
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    TMU_USERNAME = os.getenv('TMU_USERNAME')
    TMU_PASSWORD = os.getenv('TMU_PASSWORD')
    st.session_state.status = 'Launching browser...'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        st.session_state.status = 'Navigating to login...'
        page.goto('https://cas.torontomu.ca/login?service=https%3A%2F%2Frecruitstudents.torontomu.ca%2FcasLogin.htm%3Faction%3Dlogin')
        page.get_by_role('textbox', name='torontomu username').fill(TMU_USERNAME)
        page.get_by_role('textbox', name='Password').fill(TMU_PASSWORD)
        page.get_by_role('button', name='Log in').click()
        st.session_state.status = 'Waiting for 2FA page...'
        page.get_by_role('textbox', name='Verification Code:').wait_for(state='visible', timeout=60000) # Reverted to more robust locator and increased timeout
        st.session_state.waiting_2fa = True
        st.rerun()  # Trigger rerun to show prompt
        st.session_state.status = 'Waiting for 2FA code...'
        while st.session_state.get('2fa_code') is None:
            time.sleep(0.5)
        code = st.session_state['2fa_code']
        st.session_state['2fa_code'] = None
        st.session_state.waiting_2fa = False
        page.get_by_role('textbox', name='Verification Code:').fill(code)
        page.get_by_role('checkbox', name='I trust this browser on this').check()
        page.get_by_role('button', name='Log in').click()
        st.session_state.status = 'Navigating to job postings...'
        page.get_by_role("link", name="Coop").click()
        page.get_by_role('link', name='Job Postings').first.wait_for(state='visible', timeout=30000)
        page.get_by_role('link', name='Job Postings').first.click()
        page.get_by_role('link', name='Shortlist').click()
        st.session_state.status = 'Reached job page. Waiting for table to load...'
        page.wait_for_selector('#postingsTable', state='visible', timeout=30000)
        # Create jobs folder if it doesn't exist
        jobs_dir = os.path.join(os.pardir, 'jobs') # Path updated to reflect new location in root directory
        os.makedirs(jobs_dir, exist_ok=True)
        job_ids_file = os.path.join(jobs_dir, 'JobIds.txt')
        # with open(job_ids_file, 'w') as id_file:  # Clear or create the file - REMOVED TO ALLOW APPENDING
        #     pass

        # Load already scraped job IDs
        existing_job_ids = set()
        if os.path.exists(job_ids_file):
            with open(job_ids_file, 'r') as id_file:
                for line in id_file:
                    existing_job_ids.add(line.strip())

        # Find the table and loop through rows to find the first open job
        rows = page.locator('#postingsTable tbody tr')
        print(rows.count())
        jobs_scraped_count = 0 # Initialize counter for scraped jobs
        for i in range(rows.count()):
            row = rows.nth(i)
            first_td = row.locator('td:first-child').inner_text().strip()
            if first_td != '':
                # Scrape job ID from 4th <td>
                job_id_td = row.locator('td:nth-child(4)')
                job_id = job_id_td.inner_text().strip()

                if job_id in existing_job_ids:
                    st.session_state.status = f'Job {job_id} already scraped. Skipping.'
                    continue # Skip to the next job in the loop

                # Append job ID to JobIds.txt
                with open(job_ids_file, 'a') as id_file:
                    id_file.write(f'{job_id}\n')
                # Found an open job; click the link in the title column
                job_link = row.locator('td.orgDivTitleMaxWidth a')
                with page.expect_popup() as popup_info:
                    job_link.click()
                new_page = popup_info.value
                new_page.bring_to_front()  # Switch to the new tab
                st.session_state.status = f'Switched to job details page {i+1}. Waiting for tables to load...'
                new_page.wait_for_selector('table.table.table-bordered', state='visible', timeout=30000)
                # Scrape data from the first three tables
                tables = new_page.locator('table.table.table-bordered')
                if tables.count() < 3:
                    st.session_state.status = 'Not enough tables found on the page after load. Found: ' + str(tables.count())
                    # Do not break here, we need to see the content even if tables are not found.
                    # We will re-evaluate based on the HTML content.
                    # break 

                # First table: Organization Name
                first_table = tables.nth(1)
                org_name_td = first_table.locator('td[width="75%"]')
                org_name = org_name_td.inner_text().strip()

                # Second table: Specific rows
                second_table = tables.nth(2)
                second_rows = second_table.locator('tr')
                print(second_rows.count())
                work_term = second_rows.nth(0).locator('td[width="75%"]').inner_text().strip()
                job_duration = second_rows.nth(2).locator('td[width="75%"]').inner_text().strip().replace('\n', ' ') # Fix: Replace newlines with spaces
                if (second_rows.count() == 10):
                    a = 6
                    b = 8
                else:
                    a = 7
                    b = 9
                job_title = second_rows.nth(a).locator('td[width="75%"]').inner_text().strip()
                # Sanitize job_title for use in filename
                sanitized_job_title = re.sub(r'[<>:"/\\|?*]', '-', job_title)
                job_description = second_rows.nth(b).locator('td[width="75%"]').inner_text().strip()

                # Third table: Application info
                third_table = tables.nth(3)
                third_rows = third_table.locator('tr')
                deadline_date = third_rows.nth(0).locator('#npPostingApplicationInfoDeadlineDate').inner_text().strip()
                docs_required = third_rows.nth(1).locator('td[width="75%"]').inner_text().strip()
                app_method_td = third_rows.nth(2).locator('td:nth-child(2)')
                # Fix: Get only the text directly within the <td>, excluding child <a> tag text
                app_method = app_method_td.evaluate('''el => {
                    let text = '';
                    for (let node of el.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            text += node.textContent;
                        } else if (node.nodeName === 'BR' || node.nodeName === 'A') {
                            break; // Stop if we encounter a <br> or <a> tag
                        }
                    }
                    return text.trim();
                }''').strip()
                app_link = ''
                if app_method_td.locator('a').count() > 0:
                    app_link = app_method_td.locator('a').get_attribute('href')

                # Create folder for this job
                job_folder = os.path.join(jobs_dir, f'{org_name}_{job_id}')
                os.makedirs(job_folder, exist_ok=True)
                details_file = os.path.join(job_folder, f'{sanitized_job_title}_job_details.txt')
                # Write to file
                with open(details_file, 'w') as f:
                    f.write(f'Organization Name: {org_name}\n')
                    f.write(f'Work Term: {work_term}\n')
                    f.write(f'Job Duration: {job_duration}\n')
                    f.write(f'Job Title: {job_title}\n')
                    f.write(f'Job Description: {job_description}\n')
                    f.write(f'Application Deadline: {deadline_date}\n')
                    f.write(f'Documents Required: {docs_required}\n')
                    f.write(f'Application Method: {app_method}\n')
                    if app_link:
                        f.write(f'Application Link: {app_link}\n')
                st.session_state.status = f'Data scraped for job {job_title} and written to {details_file}. Processing next job...'
                # Close the job tab
                new_page.close()
                # jobs_scraped_count += 1 # Increment the counter
                # if jobs_scraped_count >= 2: # Check if two jobs have been scraped
                #     break # Exit the loop after processing 2 jobs
        time.sleep(60)
        browser.close()
        st.session_state.status = 'All open jobs scraped. Done.'
        st.session_state.running = False
        st.rerun()


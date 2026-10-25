
import os
import sys
import time
import subprocess
import urllib.request

import uuid

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture
def browser_app(tmp_path):
    external_url = os.environ.get("APP_URL")
    if external_url:
        # Running under docker compose: the app is already up in its own container.
        yield external_url
        return

    project_dir = os.path.dirname(os.path.abspath(__file__))
    database = tmp_path / "selenium.db"

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(database)
    env["PORT"] = "5001"

    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=project_dir,
        env=env
    )

    try:
        deadline = time.time() + 20

        while time.time() < deadline:
            if process.poll() is not None:
                pytest.fail("Flask server stopped unexpectedly.")

            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:5001/health",
                    timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.fail("Flask server did not start.")

        yield "http://127.0.0.1:5001"

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_report_search_and_resolve(browser_app):
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--width=1280")
    options.add_argument("--height=900")

    remote_url = os.environ.get("SELENIUM_REMOTE_URL")
    if remote_url:
        driver = webdriver.Remote(command_executor=remote_url, options=options)
    else:
        driver = webdriver.Firefox(options=options)
    driver.set_window_size(1280, 900)
    wait = WebDriverWait(driver, 10)
    item_name = f"Selenium Test Bottle {uuid.uuid4().hex[:6]}"

    try:
        # 1. Open the website.
        driver.get(browser_app)

        # 2. Open the reporting form.
        wait.until(EC.element_to_be_clickable(
            (By.LINK_TEXT, "Report an item")
        )).click()

        # 3. Fill in the report details.
        name = driver.find_element(By.ID, "name")
        name.send_keys(item_name)

        Select(
            driver.find_element(By.ID, "report_type")
        ).select_by_visible_text("I found this item")

        Select(
            driver.find_element(By.ID, "category")
        ).select_by_visible_text("Other")

        driver.find_element(By.ID, "description").send_keys(
            "Blue bottle with a black cap"
        )

        driver.find_element(By.ID, "location").send_keys(
            "Computer lab"
        )

        # 4. Verify the form values before submitting.
        assert name.get_attribute("value") == item_name
        assert Select(
            driver.find_element(By.ID, "report_type")
        ).first_selected_option.text == "I found this item"

        assert Select(
            driver.find_element(By.ID, "category")
        ).first_selected_option.text == "Other"

        # 5. Submit the report.
        driver.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()

        # 6. Confirm the report appears on the homepage.
        wait.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            item_name
        ))

        # 7. Search for the report.
        search = driver.find_element(By.ID, "search")
        search.send_keys(item_name)

        search_form = search.find_element(
            By.XPATH, "./ancestor::form"
        )
        search_form.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()

        wait.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            item_name
        ))

        # 8. Mark the item as resolved.
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Mark resolved')]")
        )).click()

        wait.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            "Item marked as resolved."
        ))

        # 9. Filter for resolved reports.
        Select(
            driver.find_element(By.ID, "status")
        ).select_by_visible_text("Resolved")

        status_form = driver.find_element(
            By.ID, "status"
        ).find_element(By.XPATH, "./ancestor::form")

        status_form.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()

        wait.until(EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"),
            item_name
        ))

    finally:
        driver.quit()

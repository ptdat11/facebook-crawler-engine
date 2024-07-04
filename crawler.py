import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER

from post import PagePostMetadata
from pipeline import Pipeline
from progress import Progress
from logger import Logger
from credentials import FacebookCookies
from extractor import FacebookPostExtractor
import colors

from typing import Literal
import bs4
import re
import logging
import numpy as np
import time
import sys
import traceback

LOGGER.setLevel(logging.CRITICAL)
total_crawler = 0

class Crawler(threading.Thread):
    """
        Base class for crawlers
    """
    def __init__(
        self,
        termination_event: threading.Event,
        progress: Progress,
        data_pipeline: Pipeline,
        headless: bool = True,
        name: str | None = None,
        mean_std_sleep_second: tuple[float, float] = (10, 1),
        DOM_wait_second: float = 90,
        thread_args: tuple = (),
        thread_kwargs: dict = {}
    ):
        global total_crawler
        total_crawler += 1
        if name is None:
            name = f"Crawler-{total_crawler}"
        super().__init__(None, self, name, *thread_args, **thread_kwargs)

        self.termination_flag = termination_event
        self.logger = Logger(name)
        self.progress = progress
        self.data_pipeline = data_pipeline

        self.headless = headless
        self.mean_std_sleep_second = mean_std_sleep_second
        self.DOM_wait_second = DOM_wait_second

        self.driver_manager = ChromeDriverManager(latest_release_url="https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.112/linux64/chrome-linux64.zip").install()
        
        self.driver_service = Service(self.driver_manager)
        self.driver_options = webdriver.ChromeOptions()
        # Options
        if headless:
            self.driver_options.add_argument("--headless")
        else: self.driver_options.add_experimental_option("detach", True)

    def new_tab(self, url: str):
        self.chrome.switch_to.new_window("tab")
        self.chrome.get(url)
        self.logger.info(f"Opened new tab to {colors.grey(url)}")

    def sleep(self, times: int = 1):
        mean, std = self.mean_std_sleep_second
        sleep_second = np.random.normal(mean, std, (times,))
        sleep_second = np.clip(sleep_second, a_min=0, a_max=mean+3*std).sum()
        time.sleep(sleep_second)

    def wait_DOM(self):
        self.chrome.implicitly_wait(self.DOM_wait_second)

    def close_all_new_tabs(self):
        for handle in self.chrome.window_handles:
            if handle == self.main_tab:
                continue
            self.chrome.switch_to.window(handle)
            self.chrome.close()
        self.chrome.switch_to.window(self.main_tab)

    def start_driver(self):
        self.chrome = webdriver.Chrome(service=self.driver_service, options=self.driver_options)
        self.main_tab = self.chrome.current_window_handle
        self.logger.info(f"Driver started")
    
    def exit(self):
        if self.termination_flag.is_set():
            self.logger.info("Closing due to Engine's termination")
        else:
            self.logger.info("Closing driver due to no URL left in queue")
        self.on_exit()
        self.chrome.quit()
    
    def on_start(self):
        pass
    
    def on_exit(self):
        pass
    
    def parse(self, url: str):
        pass

    def on_parse_error(self):
        pass

    def run(self):
        self.start_driver()
        self.on_start()
        err_trial = 0

        while (
            self.progress.remaining_num() > 0 
            and not self.termination_flag.is_set()
            and err_trial <= 5
        ):
            try:
                # Extract data -> Pipeline -> Add history
                url = self.progress.next_url()
                self.logger.info(f"Begin parsing {colors.grey(url)}")
                data = self.parse(url)
                self.data_pipeline(data)
                self.progress.add_history(url) 
                self.sleep()
                err_trial = 0
            except:
                err_trial += 1
                # Logging out error
                exc_type, value, tb = sys.exc_info()
                self.logger.error(f"Restore {colors.grey(url)} to queue due to error: \n{colors.red(exc_type.__name__)}: {value}\n{traceback.format_exc()}")
                # If this url hasn't been crawled successfully
                if not self.progress.propagated(url):
                    # Re-append URL to queue
                    self.progress.enqueue(url, "left")

                self.on_parse_error()
        self.exit()


class FacebookPageCrawler(Crawler):
    def __init__(
        self, 
        termination_event: threading.Event,
        progress: Progress,
        data_pipeline: Pipeline,
        email: str,
        password: str,
        headless: bool = True,
        cookies_dir: str = "./fb-cookies",
        name: str | None = None,
        mode: Literal["post", "comments", "both"] = "both",
        comment_load_num: int = 300,
        mean_std_load_cmt_sleep_second: tuple[float, float] = (1, 0.1),
        mean_std_sleep_second: tuple[float, float] = (6, 1),
        DOM_wait_second: float = 60,
        thread_args: tuple = (),
        thread_kwargs: dict = {}
    ) -> None:
        super().__init__(
            termination_event=termination_event,
            progress=progress,
            data_pipeline=data_pipeline,
            headless=headless,
            name=name,
            mean_std_sleep_second=mean_std_sleep_second, 
            DOM_wait_second=DOM_wait_second, 
            thread_args=thread_args, 
            thread_kwargs=thread_kwargs
        )
        self.email = email
        self.password = password
        self.mode = mode
        self.cmt_load_num = comment_load_num
        self.cookies = FacebookCookies(cookies_dir)
        self.mean_std_cmt_sleep = mean_std_load_cmt_sleep_second 
    
    def load_cookies(self):
        self.chrome.get("https://mbasic.facebook.com")
        for cookie in self.cookies.load():
            self.chrome.add_cookie(cookie)

    def on_parse_error(self):
        if not self.termination_flag.is_set():
            self.close_all_new_tabs()
        self.load_cookies()
        
    def on_start(self):
        self.post_extractor = FacebookPostExtractor(
            chrome=self.chrome, 
            logger=self.logger,
            mode=self.mode,
            cmt_load_time=self.cmt_load_num,
            mean_std_sleep_second=self.mean_std_cmt_sleep,
            DOM_wait_second=self.DOM_wait_second
        )

        # If local doesn't have cookies
        if not self.cookies.exists():
            self.login()

            cookies = self.chrome.get_cookies()
            self.cookies.save(cookies)
            self.logger.info("Saved current cookies for future Facebook access")
        # If local has already stored cookies
        else:
            self.load_cookies()

            # Refresh cookies
            self.chrome.refresh()
            self.cookies.save(self.chrome.get_cookies())
            self.logger.info("Refreshed cookies")
        self.sleep()
    
    def login(self):
        self.chrome.get("https://mbasic.facebook.com")
        self.sleep()

        # Get input elements
        email_input = self.chrome.find_element(By.NAME, "email")
        pass_input = self.chrome.find_element(By.NAME, "pass")

        # Fill the form
        email_input.send_keys(self.email)
        pass_input.click()
        pass_input.send_keys(self.password)

        # Submit form
        login_btn = self.chrome.find_element(By.NAME, "login")
        login_btn.click()

        # Wait a bit
        self.sleep()

        # Remember this device
        remember_device_btn = self.chrome.find_element(By.XPATH, "//input[(@value='OK') and (@class = 'bo bp bq br bs')]")
        remember_device_btn.click()
    
    def parse(self, url: str):
        self.chrome.get(url)
        self.wait_DOM()
        self.sleep()
        container = self.chrome.find_element(By.ID, "structured_composer_async_container")
        
        posts: list[WebElement] = (
            container
            .find_element(By.TAG_NAME, "section")
            .find_elements(By.XPATH, "article")
        )
        self.logger.info("Located {0} posts".format(colors.bold(str(len(posts)))))

        # Switch off login session, reducing account traffic
        self.chrome.delete_all_cookies()
        data = []
        for i, post in enumerate(posts):
            metadata = PagePostMetadata(post)
            # self.logger.info("Extracted metadata for {0} post".format(colors.bold(str(i+1)+"th")))

            # If this post contains image(s), go to new tab and crawl
            if (
                "image" in metadata.attachment_types 
                # and metadata.preview_text != "" 
                and not self.progress.propagated(metadata.post_url)
            ):
                self.new_tab(metadata.post_url)
                self.chrome.find_element(By.XPATH, "//div[@role='button' and @aria-label='Close']").click()
                post_data = self.post_extractor.extract(metadata)
                data.extend(post_data)

                self.progress.add_history(metadata.post_url)
                self.close_all_new_tabs()

        next_page_el: WebElement = container.find_element(By.XPATH, "div")
        next_page_el: WebElement = next_page_el.find_element(By.TAG_NAME, "a")
        next_page_link = next_page_el.get_attribute("href") \
                        if next_page_el is not None \
                        else None
        self.progress.enqueue(next_page_link)

        # Turn back on the login session, for propagating across the page
        self.load_cookies()

        return data

    def cmt_show_mode(self, mode: Literal["newest", "most relevant", "all"] = "most relevant"):
        btn_div = self.chrome.find_element(By.CSS_SELECTOR, "div.x78zum5.x1n2onr6.x1nhvcw1")
        if len(btn_div.find_elements(By.XPATH, "*")) == 0:
            return

        mode = {
            "newest": 1,
            "most relevant": 2,
            "all": 3
        }[mode]
        WebDriverWait(self.chrome, self.mean_std_sleep_second[0]) \
            .until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@class='x9f619 x1n2onr6 x1ja2u2z xt0psk2 xuxw1ft']")
            )).click()
        WebDriverWait(
            self.chrome.find_element(By.XPATH, "//div[@class='x4k7w5x x1h91t0o x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1n2onr6 x1qrby5j x1jfb8zj']"),
            self.mean_std_sleep_second[0]
        ) .until(EC.element_to_be_clickable(
            (By.XPATH, f"(//div[@role='menuitem'])[{mode}]")
        )).click()
    
    def show_all_replies(self):
        cnt = 0
        while cnt <= self.cmt_load_num:
            if len(bs4.BeautifulSoup(
                self.chrome.find_element(By.XPATH, "//div[@class = 'x1pi30zi x1swvt13 x1n2onr6']").find_element(By.XPATH, "//div[@class = 'x1gslohp']").get_attribute("innerHTML"),
                "lxml"
            ).find_all(
                "div",
                attrs={"class": "x78zum5 x1iyjqo2 x21xpn4 x1n2onr6"}
            )) == 0:
                break

            all_replied_comments = self.chrome.find_element(By.XPATH, "//div[contains(@class, 'x78zum5 x1iyjqo2 x21xpn4 x1n2onr6')][last()]")
            for comment in all_replied_comments:
                cnt += 1
                self.chrome.execute_script("window.scrollBy(0, -50);")  # Cuộn lên 50 dòng
                try:
                    view_more_buttons = WebDriverWait(comment, 5).until(EC.element_to_be_clickable(comment))
                    view_more_buttons.click()
                except Exception as e:
                    break

                mean, std = self.mean_std_cmt_sleep
                time.sleep(
                    np.clip(np.random.normal(mean, std), 0, mean+3*std)
                )
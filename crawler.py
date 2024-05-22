import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.remote_connection import LOGGER

from post import PagePostMetadata
from pipeline import Pipeline
from progress import Progress
from logger import Logger
from credentials import FacebookCookies
import colors

from typing import Iterable
import re
import logging
import getpass
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
        name: str | None = None,
        mean_std_sleep_second: tuple[float, float] = (10, 1),
        DOM_wait_second: float = 90,
        thread_args: Iterable = (),
        thread_kwargs: dict = {}
    ):
        global total_crawler
        total_crawler += 1
        if name is None:
            name = f"Crawler-{total_crawler}"
        super().__init__(None, self, name, *thread_args, **thread_kwargs)

        self.termination_event = termination_event
        self.logger = Logger(name)
        self.progress = progress
        self.data_pipeline = data_pipeline

        self.mean_std_sleep_second = mean_std_sleep_second
        self.DOM_wait_second = DOM_wait_second

        self.driver_manager = ChromeDriverManager(latest_release_url="https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.60/linux64/chrome-linux64.zip").install()
        self.driver_service = Service(self.driver_manager)
        self.driver_options = webdriver.ChromeOptions()
        # Options
        self.driver_options.add_experimental_option("detach", True)
        # self.driver_options.add_experimental_option(
        #     "prefs", {"profile.managed_default_content_settings.images": 2}
        # )

    def start_driver(self):
        self.chrome = webdriver.Chrome(service=self.driver_service, options=self.driver_options)
        self.main_tab = self.chrome.current_window_handle
        self.logger.info(f"Driver started")
    
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

    def close_all(self):
        for handle in self.chrome.window_handles:
            self.chrome.switch_to.window(handle)
            self.chrome.close()
    
    def close_all_new_tabs(self):
        for handle in self.chrome.window_handles:
            if handle == self.main_tab:
                continue
            self.chrome.switch_to.window(handle)
            self.chrome.close()
        self.chrome.switch_to.window(self.main_tab)
    
    def on_start(self):
        pass

    def on_exit(self):
        pass
    
    def parse(self, url: str):
        pass

    def on_page_parse_error(self):
        self.close_all_new_tabs()

    def run(self):
        self.start_driver()
        self.on_start()

        while self.progress.remaining_num() > 0:
            if self.termination_event.is_set():
                self.logger.warning("Closing due to Engine's termination")
                break
            try:
                # Extract data -> Pipeline -> Add history
                url = self.progress.next_url()
                data = self.parse(url)
                self.data_pipeline(data)
                self.progress.add_history(url)
            except:
                self.on_page_parse_error()

                # Logging out error
                exc_type, value, tb = sys.exc_info()
                self.logger.error(f"Restore {colors.grey(url)} to queue due to error: \n{colors.red(exc_type.__name__)}: {value}\n{traceback.format_exc()}")

                # If this url hasn't been crawled successfully
                if not self.progress.propagated(url):
                    # Re-append URL to queue
                    self.progress.enqueue(url, "left")

        if not self.termination_event.is_set():
            self.logger.info("Closing driver due to no URL left in queue")
        else:
            self.logger.info("Exitting")
        self.on_exit()
        self.close_all()


class FacebookPageCrawler(Crawler):
    def __init__(
        self, 
        termination_event: threading.Event,
        progress: Progress,
        data_pipeline: Pipeline,
        cookies_dir: str = "./fb-cookies",
        name: str | None = None,
        mean_std_sleep_second: tuple[float, float] = (6, 1),
        DOM_wait_second: float = 60,
        thread_args: Iterable = (),
        thread_kwargs: dict = {}
    ) -> None:
        super().__init__(
            termination_event=termination_event,
            progress=progress,
            data_pipeline=data_pipeline,
            name=name,
            mean_std_sleep_second=mean_std_sleep_second, 
            DOM_wait_second=DOM_wait_second, 
            thread_args=thread_args, 
            thread_kwargs=thread_kwargs
        )
        self.cookies = FacebookCookies(cookies_dir)

    def on_page_parse_error(self):
        pass
        
    def on_start(self):
        if not self.cookies.exists():
            self.login()

            cookies = self.chrome.get_cookies()
            self.cookies.save(cookies)
        else:
            self.chrome.get("https://mbasic.facebook.com")
            for cookie in self.cookies.load():
                self.chrome.add_cookie(cookie)
        self.sleep()
    
    def on_exit(self):
        cookies = self.chrome.get_cookies()
        self.cookies.save(cookies)
        self.logger.info("Saved cookies")
    
    def login(self):
        self.chrome.get("https://mbasic.facebook.com")
        self.sleep()

        # Get input elements
        email_input = self.chrome.find_element(By.NAME, "email")
        pass_input = self.chrome.find_element(By.NAME, "pass")

        email = input(colors.bold("Your email:"))
        password = getpass.getpass(colors.bold("Enter password:"))

        # Fill the form
        email_input.send_keys(email)
        pass_input.click()
        pass_input.send_keys(password)

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
        self.logger.info(f"Begin parsing {colors.grey(url)}")
        container = self.chrome.find_element(By.ID, "structured_composer_async_container")
        
        posts: list[WebElement] = (
            container
            .find_element(By.TAG_NAME, "section")
            .find_elements(By.XPATH, "article")
        )
        self.logger.info("{0} posts located successfully".format(colors.bold(str(len(posts)))))

        data = []
        for i, post in enumerate(posts):
            metadata = PagePostMetadata(post)
            # self.logger.info("Extracted metadata for {0} post".format(colors.bold(str(i+1)+"th")))

            # If this post contains image(s), go to new tab and crawl
            if (
                "image" in metadata.attachment_types 
                and metadata.preview_text != "" 
                and not self.progress.propagated(metadata.post_url)
            ):
                self.new_tab(metadata.post_url)
                text, images = self.parse_post()

                sample = {
                    "page_id": metadata.page_id,
                    "post_id": metadata.post_id,
                    "post_url": metadata.post_url,
                    "datetime": metadata.date,
                    "text": text,
                    "images": images
                }
                data.append(sample)

                self.progress.add_history(metadata.post_url)
                self.close_all_new_tabs()

        next_page_el: WebElement = container.find_element(By.XPATH, "div")
        next_page_el: WebElement = next_page_el.find_element(By.TAG_NAME, "a")
        next_page_link = next_page_el.get_attribute("href") \
                        if next_page_el is not None \
                        else None
        self.progress.enqueue(next_page_link)

        return data

    def parse_post(self):
        self.wait_DOM()
        self.sleep()
        html_divs = self.chrome.find_elements(By.CLASS_NAME, "html-div")
        text_div, img_div = html_divs[8].find_elements(By.XPATH, "div")
        img_div = img_div.find_element(By.XPATH, "div")

        text = self.parse_post_text(text_div)
        images = "   ".join([
            img.get_attribute("src")
            for img in img_div.find_elements(By.TAG_NAME, "img")
        ])
        return text, images
    
    def parse_post_text(self, text_div: WebElement):
        text = text_div.get_attribute("innerHTML")
        text = re.sub(r"(<img[^>]*alt=\"([^\"]+)\")[^>]*>", r"\2", text)
        text = re.sub(r"(?<=</div>)()(?=<div)", r"\n", text)
        text = re.sub(r"<.*?>", "", text)
        return text
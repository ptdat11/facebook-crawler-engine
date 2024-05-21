import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from post import PagePostMetadata
from pipeline import Pipeline
from progress import Progress
from logger import Logger
from credentials import FacebookCookies
import colors

from typing import Iterable
import getpass
import numpy as np
import time
import sys
import traceback

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
        self.driver_options.add_experimental_option("detach", True)

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

    def on_page_parse_error(self):
        pass
    
    def on_start(self):
        pass
    
    def parse(self, url: str):
        pass
    
    def run(self):
        self.chrome = webdriver.Chrome(service=self.driver_service, options=self.driver_options)
        self.logger.info(f"Driver started")

        # What to do before crawling
        self.on_start()
        # If there exists URLs in queue
        while self.progress.remaining_num() > 0:
            if self.termination_event.is_set():
                self.logger.warning("Closing due to Engine's termination")
                for handle in self.chrome.window_handles:
                    self.chrome.switch_to.window(handle)
                    self.chrome.close()
                sys.exit()
            try:
                # Extract 1
                url = self.progress.next_url()
                # Get data
                data = self.parse(url)
                # Put data into Pipeline for whatever task
                self.data_pipeline(data)
                # Add URL to history once done
                self.progress.add_history(url)
            except:
                self.on_page_parse_error()
                exc_type, value, tb = sys.exc_info()
                # # If this url hasn't been crawled successfully
                self.logger.error(f"Restore {colors.grey(url)} to queue due to error \n{colors.red(exc_type.__name__)}: {value}\n{traceback.format_exc()}")
                if not self.progress.propagated(url):
                #     # Re-append URL to queue
                    self.progress.enqueue(url, "left")
                    if self.termination_event.is_set():
                        break

        self.logger.info("Closing driver due to no URL left in queue")
        self.chrome.close()


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
    
    def on_page_parse_error(self):
        pass
    
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
        current_tab_handle = self.chrome.current_window_handle
        self.logger.info("Extracted posts successfully")

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
                self.chrome.close()
                self.chrome.switch_to.window(current_tab_handle)

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
        text = text_div.text
        images = "   ".join([
            img.get_attribute("src")
            for img in img_div.find_elements(By.TAG_NAME, "img")
        ])
        return text, images
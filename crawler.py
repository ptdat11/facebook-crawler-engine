import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from post import PagePostMetadata
from pipeline import Pipeline

from collections import deque
from typing import Iterable
import numpy as np
import time

total_crawler = 0

class Crawler(threading.Thread):
    """
        Base class for crawlers
    """
    def __init__(
        self,
        queue: deque,
        history: set,
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

        self.queue = queue
        self.history = history
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

    def sleep(self, times: int = 1):
        mean, std = self.mean_std_sleep_second
        sleep_second = np.random.normal(mean, std, (times,))
        sleep_second = np.clip(sleep_second, a_min=0, a_max=mean+3*std).sum()
        time.sleep(sleep_second)

    def wait_DOM(self):
        self.chrome.implicitly_wait(self.DOM_wait_second)
    
    def save_history(self, url: str):
        self.history.add(url)
    
    def enqueue(self, url: str):
        self.queue.append(url)
    
    def next_url(self):
        return self.queue.popleft()
    
    def on_start(self):
        pass
    
    def parse(self, url: str):
        pass
    
    def run(self):
        self.chrome = webdriver.Chrome(service=self.driver_service, options=self.driver_options)
        print(f"{self.name} started")

        # What to do before crawling
        self.on_start()
        # If there exists URLs in queue
        while len(self.queue) > 0:
            try:
                # Extract 1
                url = self.next_url()
                # Get data
                data = self.parse(url)
                # Put data into Pipeline for whatever task
                self.data_pipeline(data)
                # Add URL to history once done
                self.history.add(url)
            except:
                # If this url hasn't been crawled successfully
                if url not in self.history:
                    # Re-append URL to queue
                    self.queue.appendleft(url)


class FacebookPageCrawler(Crawler):
    def __init__(
        self, 
        email: str,
        password: str,
        queue: deque,
        history: set,
        data_pipeline: Pipeline,
        name: str | None = None,
        mean_std_sleep_second: tuple[float, float] = (10, 1),
        DOM_wait_second: float = 60,
        thread_args: Iterable = (),
        thread_kwargs: dict = {}
    ) -> None:
        super().__init__(
            queue=queue, 
            history=history,
            data_pipeline=data_pipeline,
            name=name,
            mean_std_sleep_second=mean_std_sleep_second, 
            DOM_wait_second=DOM_wait_second, 
            thread_args=thread_args, 
            thread_kwargs=thread_kwargs
        )

        self.email = email
        self.password = password
        
    def on_start(self):
        self.login()
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
        posts: list[WebElement] = self.chrome.find_elements(By.TAG_NAME, "article")
        current_tab_handle = self.chrome.current_window_handle

        data = []
        for post in posts:
            metadata = PagePostMetadata(post)

            # If this post contains image(s), go to new tab and crawl
            if (
                "image" in metadata.attachment_types 
                and metadata.preview_text != "" 
                and metadata.post_id not in self.history
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
                self.chrome.close()
                self.chrome.switch_to.window(current_tab_handle)

        next_page_el: WebElement = self.chrome.find_element(By.ID, "structured_composer_async_container").find_element(By.XPATH, "div")
        next_page_el: WebElement = next_page_el.find_element(By.TAG_NAME, "a")
        next_page_link = next_page_el.get_attribute("href") \
                        if next_page_el is not None \
                        else None
        self.enqueue(next_page_link)

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
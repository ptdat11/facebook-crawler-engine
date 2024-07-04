from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
import bs4

import numpy as np
import re
import time
import colors
from typing import Literal
from logger import Logger
from post import PagePostMetadata

class Extractor:
    def __init__(
        self,
        chrome: webdriver.Chrome,
        logger: Logger,
        mean_std_sleep_second: tuple[float, float] = (6, 1),
        DOM_wait_second: float = 60
    ) -> None:
        self.chrome = chrome
        self.logger = logger
        self.mean_std_sleep_second = mean_std_sleep_second
        self.DOM_wait_second = DOM_wait_second
    
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

    def extract(self):
        pass


class FacebookPostExtractor(Extractor):
    def __init__(
        self,
        chrome: webdriver.Chrome,
        logger: Logger,
        mode: Literal["post", "comments", "both"] = "both",
        cmt_load_time: int = 0,
        mean_std_sleep_second: tuple[float, float] = (6, 1),
        DOM_wait_second: float = 60
    ):
        super().__init__(
            chrome=chrome, 
            logger=logger, 
            mean_std_sleep_second=mean_std_sleep_second,
            DOM_wait_second=DOM_wait_second
        )
        self.mode = mode
        self.cmt_load_time = cmt_load_time
    
    def extract(self, metadata: PagePostMetadata):
        data = []

        if self.mode in ["post", "both"]:
            self.logger.info("Parsing post's content...")
            text, images = self.extract_post()
            post_data = {
                "page_id": metadata.page_id,
                "post_id": metadata.post_id,
                "post_url": metadata.post_url,
                "cmt_id": "",
                "cmt_url": "",
                "datetime": metadata.date,
                "text": text,
                "images": images,
                "type": "post"
            }
            data.append(post_data)

        if self.mode in ["comment", "both"]:
            self.logger.info("Parsing comments...")
            cmt_data = self.extract_comments(post_data)
            cmt_data = [
                {
                    "page_id": metadata.page_id,
                    "post_id": metadata.post_id,
                    "post_url": metadata.post_url,
                    "cmt_id": cmt["id"],
                    "cmt_url": cmt["url"],
                    "datetime": metadata.date,
                    "text": cmt["text"],
                    "images": cmt["image"],
                    "type": "comment"
                }
                for cmt in cmt_data
            ]
            data.extend(cmt_data)
        
        return data
    
    def extract_post(self):
        html_divs = self.chrome.find_elements(By.CLASS_NAME, "html-div")
        text_div, img_div = html_divs[7].find_elements(By.XPATH, "div")
        img_div = img_div.find_element(By.XPATH, "div").find_element(By.XPATH, "*").find_element(By.XPATH, "*").find_element(By.XPATH, "*")

        text = self.parse_text(text_div)
        images = "   ".join([
            img.get_attribute("src")
            for img in img_div.find_elements(By.TAG_NAME, "img")
        ])
        return text, images

    def extract_comments(self, post_data: dict):
        data = []
        comments = self.chrome.find_elements(By.CSS_SELECTOR, "div.x1r8uery.x1iyjqo2.x6ikm8r.x10wlt62.x1pi30zi")
        self.logger.info(f"Located {colors.bold(len(comments))} comments")

        for i, comment in enumerate(comments):
            raw_cmt_url = comment.find_element(By.XPATH, "div[@class='x6s0dn4 x3nfvp2']").find_element(By.TAG_NAME, "a").get_attribute("href")

            attachment_type = self.extract_cmt_attachment_type(comment)

            text_div: WebElement = (
                comment
                .find_element(By.CSS_SELECTOR, "div")
                .find_element(By.CSS_SELECTOR, "div")
                .find_element(By.CSS_SELECTOR, "div")
                .find_element(By.CSS_SELECTOR, "div")
            )
            if attachment_type == "no attachment":
                text_div = text_div.find_element(By.CSS_SELECTOR, "div").find_element(By.CSS_SELECTOR, "div")
            text_div = text_div.find_elements(By.XPATH, "*")[-1]

            if text_div.get_attribute("class") != "x1lliihq xjkvuk6 x1iorvi4":
                continue
            text_soup = bs4.BeautifulSoup(text_div.get_attribute("innerHTML"), "lxml")
            if text_soup.find(
                "div",
                attrs={
                    "role": "button",
                    "tabindex": "0"
                },
                string="See more"
            ) is not None:
                if len(self.chrome.find_element(By.CSS_SELECTOR, "div[data-nosnippet]").find_elements(By.XPATH, "*")) > 0:
                    self.chrome.execute_script("""
                        var l = document.querySelector("div[data-nosnippet]");
                        l.removeChild(l.firstChild);
                    """)
                
                see_more_btn: WebElement = text_div.find_element(By.XPATH, "//div[@role='button' and text()='See more']")
                ActionChains(self.chrome).move_to_element(see_more_btn).perform()
                see_more_btn.click()
            
            text = self.parse_text(text_div)
            cmt_id = re.search(r"comment_id=(\d+)", raw_cmt_url).group(1)
            cmt_url = f"https://facebook.com/{cmt_id}"

            if attachment_type == "no attachment":
                data.append({
                    "id": cmt_id,
                    "url": cmt_url,
                    "text": text,
                    "image": post_data["images"]
                })
            elif attachment_type == "image":
                img = comment.find_element(By.TAG_NAME, "div.x78zum5.xv55zj0.x1vvkbs").find_element(By.CSS_SELECTOR, "img.xz74otr")
                
                self.logger.info(f"Getting {i+1}th comment's image")
                img_src = self.parse_cmt_img(img)

                data.append({
                    "id": cmt_id,
                    "url": cmt_url,
                    "text": text,
                    "image": img_src,
                })
        return data
    
    def parse_cmt_img(self, img_element: WebElement):
        href = img_element.find_element(By.XPATH, "./..").get_attribute("href")
        current_handle = self.chrome.current_window_handle
        self.new_tab(href)
        self.wait_DOM()
        self.sleep()

        page_soup = bs4.BeautifulSoup(self.chrome.page_source, "lxml")
        img = page_soup.find(
            "img",
            attrs={"data-visualcompletion": "media-vc-image"}
        )
        src = img.attrs["src"]

        self.chrome.close()
        self.chrome.switch_to.window(current_handle)

        self.sleep()
        
        return src

    def extract_cmt_attachment_type(self, cmt_div: WebElement):
        content_divs: list[WebElement] = cmt_div.find_elements(By.XPATH, "div")

        # print("Checking none")
        if content_divs[1].get_attribute("class") != "x78zum5 xv55zj0 x1vvkbs":
            return "no attachment"
        attm_div = content_divs[1]
        attm_soup = bs4.BeautifulSoup(attm_div.get_attribute("innerHTML"), "lxml")

        # print("Checking video")
        if attm_soup.find(
            "video",
            attrs={"class": "x1lliihq x5yr21d xh8yej3"}
        ):
            return "video"

        # print("Checking link")
        if attm_soup.find(
            "a",
            attrs={"class": "x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1ey2m1c xds687c x10l6tqk x17qophe x13vifvy xi2jdih"}
        ):
            return "link"

        # print("Checking sticker")
        if attm_soup.find(
            "img",
            attrs={"class": "xz74otr x1uzojwf x10e4vud xa4qsjk xoj058f x1nxgg22 x10l6tqk x17qophe x13vifvy"}
        ):
            return "sticker"

        # print("Checking gif")
        if attm_soup.find(
            "div",
            attrs={"class": "x1i10hfl x1ypdohk xe8uvvx x1hl2dhg xggy1nq x1o1ewxj x3x9cwd x1e5q0jg x13rtm0m x87ps6o x1lku1pv x1a2a7pz xjyslct xjbqb8w x13fuv20 xu3j5b3 x1q0q8m5 x26u7qi x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x5muytz x1lliihq x5yr21d xdj266r x11i5rnm xat24cr x1mh8g0r x6ikm8r x10wlt62 xexx8yu x4uap5 x18d9i69 xkhd6sd x1n2onr6 x16tdsg8 xh8yej3 x1ja2u2z"}
        ) or attm_soup.find(
            "img",
            attrs={"class": "xz74otr x1lliihq xt7dq6l x193iq5w"}
        ):
            return "gif"

        # print("Checking image")
        if attm_soup.find(
            "img",
            attrs={"class": "xz74otr"}
        ):
            return "image"

        return "unknown"
    
    def parse_text(self, text_element: WebElement):
        text = text_element.get_attribute("innerHTML")
        text = re.sub(r"(<img[^>]*alt=\"([^\"]+)\")[^>]*>", r"\2", text)
        text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"href(\2, \1)", text)
        text = re.sub(r"(?<=</div>)()(?=<div)", r"\n", text)
        text = re.sub(r"<.*?>", "", text)
        return text
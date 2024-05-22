from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import selenium.common.exceptions as exc

from datetime import datetime, time, timedelta
import re
from urllib.parse import urlparse
from typing import Sequence, Literal

HREF_TYPE: dict[str, Literal["image", "video", "link"]] = {
    "/photo.php": "image",
    "/video_redirect/": "video",
    "/l.php": "link",
    "shared post": "shared post",
    "avatar / background": "avatar / background"
}

class PagePostMetadata:
    def __init__(
        self,
        post_element: WebElement,
    ) -> None:
        header: WebElement = post_element.find_element(By.TAG_NAME, "header")
        content: list[WebElement] = post_element.find_element(By.TAG_NAME, "div").find_elements(By.XPATH, "div")
        footer: WebElement = post_element.find_element(By.TAG_NAME, "footer")

        date_div, like_div = footer.find_elements(By.XPATH, "div")
        post_id = like_div.find_element(By.TAG_NAME, "span").get_attribute("id")
        page_id = header.find_element(By.TAG_NAME, "a").get_attribute("href")
        page_id = urlparse(page_id).path.strip("/")
        page_name_h3: WebElement = header.find_element(By.TAG_NAME, "h3")
        
        post_id = re.sub(r"^like_([\d]+)$", r"\1", post_id)
        raw_date = re.sub(r"([\d\w\s]+)\s·[\s\w\d]+$", r"\1", date_div.text)

        if len(content) > 1:
            attachment_element: WebElement = content[1].find_element(By.XPATH, "(div)[1]")
            attachment_element = attachment_element.find_element(By.XPATH, "//*")
            if attachment_element.tag_name == "article":
                attachment_hrefs = ["shared post"]
            elif "đã cập nhật" in page_name_h3.text:
                attachment_hrefs = ["avatar / background"]
            else:
                attachment_hrefs = [
                    a.get_attribute("href")
                    for a in content[1].find_elements(By.TAG_NAME, "a")
                ]
        else: attachment_hrefs = []

        self.date, self.attachment_types = self.parse_data(raw_date, attachment_hrefs)
        self.page_id = page_id
        self.post_id = post_id
        self.post_url = f"https://facebook.com/{self.post_id}"
        self.preview_text = content[0].text
    
    def parse_data(
        self,
        raw_date: str,
        attachment_hrefs: Sequence[str]
    ):
        date = parse_post_date(raw_date)
        attachment_types = parse_attachment_types(attachment_hrefs)

        return date, attachment_types
    
    def to_json(self):
        return {
            "page_id": self.page_id,
            "post_id": self.post_id,
            "post_url": self.post_url,
            "date": self.date,
            "preview_text": self.preview_text,
            "attachment_types": self.attachment_types
        }


def parse_post_date(raw_date: str):
    dt = datetime.now()
    if "tháng" in raw_date:
        if "," not in raw_date:
            year = str(datetime.now().year)
            raw_date = f", {year}".join(
                re.split(r"(?<=\d)(?= lúc)", raw_date)
            )
        dt = datetime.strptime(raw_date, "%d tháng %m, %Y lúc %H:%M")
    elif "phút" in raw_date:
        minute = re.search(r"(\d{1,2}) phút", raw_date).group(1)
        minute = int(minute)
        dt -= timedelta(minutes=minute)
    elif "giờ" in raw_date:
        hour = re.search(r"(\d{1,2}) giờ", raw_date).group(1)
        hour = int(hour)
        dt -= timedelta(hours=hour)
    elif "Hôm qua" in raw_date:
        h_m_search = re.search(r"lúc (\d{1,2}):(\d{2})$", raw_date)
        hour, minute = h_m_search.group(1), h_m_search.group(2)
        dt -= timedelta(days=1)
        dt.replace(hour=int(hour), minute=int(minute))
    return dt

def parse_attachment_types(attachment_hrefs: Sequence[str]):
    return [
        HREF_TYPE.get(urlparse(href).path, "unknown")
        for href in attachment_hrefs
    ]
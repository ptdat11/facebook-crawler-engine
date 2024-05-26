from engine import Engine
from crawler import FacebookPageCrawler
from pipeline import Pipeline, SaveAsCSV
import colors
import getpass

email = "ptdat01012003@outlook.com"
password = getpass.getpass()

page_ids = [
    "colinkkhong",
    "chonlonglay",
    "ChiHieuHon"
]
num_crawlers = len(page_ids)
group_name = "_".join(page_ids)

data_pipeline = Pipeline(
    SaveAsCSV(
        f"./data/{group_name}/{group_name}.csv",
        transform_to_dframe=True
    )
)

engine = Engine(
    crawler_type=FacebookPageCrawler,
    start_urls=[f"https://mbasic.facebook.com/{id}?v=timeline" for id in page_ids],
    data_pipeline=data_pipeline,
    progress_dir=f"./data/{group_name}/progress",
    num_crawlers=num_crawlers,
    name_format=f"Crawler-{colors._bold}{{0}}",
    crawler_kwargs={
        "email": email,
        "password": password,
        "headless": False,
        "mean_std_sleep_second": (4, 1),
        "DOM_wait_second": 90,
        "comment_load_num": 30,
        "cookies_dir": "./cookies"
    }
)
engine.run()
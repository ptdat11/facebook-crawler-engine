from engine import Engine
from crawler import FacebookPageCrawler
from pipeline import Pipeline, SaveImages, SaveAsCSV
import colors
import getpass

email = ""
password = ""

data_dir = "kltn"
page_ids = [
    "BeatvnNow"
]
num_crawlers = len(page_ids)
group_name = "_".join(page_ids)

data_pipeline = Pipeline(
    SaveImages(
        save_dir=f"{data_dir}/{group_name}/imgs",
        img_col="images",
        img_name_format="{post_id}_{cmt_id}_{ordinal}.jpg"
    ),
    SaveAsCSV(f"{data_dir}/{group_name}/{group_name}.csv")
)

engine = Engine(
    crawler_type=FacebookPageCrawler,
    start_urls=[f"https://mbasic.facebook.com/{id}?v=timeline" for id in page_ids],
    data_pipeline=data_pipeline,
    progress_dir=f"{data_dir}/{group_name}/progress",
    num_crawlers=num_crawlers,
    name_format=f"Crawler-{colors._bold}{{0}}",
    crawler_kwargs=dict(
        email=email,
        password=password,
        headless=False,
        mean_std_sleep_second=(13, 4),
        mean_std_load_cmt_sleep_second=(1, 2),
        DOM_wait_second=90,
        mode="both",
        comment_load_num=0,
        cookies_dir="./fb-cookies"
    )
)
engine.run()
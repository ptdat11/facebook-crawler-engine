from engine import Engine
from crawler import FacebookPageCrawler
from pipeline import Pipeline, SaveAsCSV
import colors
import getpass

email = ""
password = ""

# page_ids = [
#     "colinkkhong",
#     "chonlonglay",
#     "ChiHieuHon"
# ]
page_ids = [
    "trollbongda",
    "trollxe.vietnam",
    "www.voz.vn"
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
    crawler_kwargs=dict(
        email=email,
        password=password,
        headless=True,
        mean_std_sleep_second=(8, 1),
        DOM_wait_second=90,
        comment_load_num=0,
        cookies_dir="./fb-cookies"
    )
)
engine.run()
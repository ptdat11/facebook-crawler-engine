from engine import Engine
from crawler import FacebookPageCrawler
from pipeline import Pipeline, SaveAsCSV

page_ids = [
    "ThoBayMau",
    "EnComics"
]

data_pipeline = Pipeline(
    SaveAsCSV(
        "posts.csv",
        columns=["page_id", "post_id", "post_url", "datetime", "text", "images"]
    )
)

engine = Engine(
    crawler_type=FacebookPageCrawler,
    start_urls=[f"https://mbasic.facebook.com/{id}?v=timeline" for id in page_ids],
    data_pipeline=data_pipeline,
    progress_dir="./progress-1",
    num_crawlers=2,
    name_format="Facebook Crawler-{0}",
    crawler_kwargs={
        "mean_std_sleep_second": (6, 1),
        "DOM_wait_second": 90,
    }
)
engine.run()
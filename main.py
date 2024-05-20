from engine import Engine
from crawler import FacebookPageCrawler
from pipeline import Pipeline, SaveAsCSV
import getpass

email = "ptdat01012003@outlook.com"
pw = getpass.getpass()

page_ids = [
    "ThoBayMau",
    "EnComics"
]
data_pipeline = Pipeline(
    SaveAsCSV(
        "posts.csv",
        columns=["page_id", "post_id", "post_url", "datetime", "text", "images"],
        append_existing=True
    )
)

engine = Engine(
    crawler_type=FacebookPageCrawler,
    start_urls=[f"https://mbasic.facebook.com/{id}?v=timeline" for id in page_ids],
    data_pipeline=data_pipeline,
    name_format="Facebook Crawler-{0}",
    crawler_kwargs={
        "email": email,
        "password": pw
    }
)
engine.run()
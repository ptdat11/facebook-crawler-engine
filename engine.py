from crawler import Crawler
from collections import deque
from pipeline import Pipeline

from typing import Sequence, Type

class Engine:
    def __init__(
        self,
        crawler_type: Type[Crawler],
        start_urls: Sequence[str],
        data_pipeline: Pipeline,
        progress_path: str = "./progress/",
        num_crawlers: int = 1,
        name_format: str = "Crawler-{0}",
        crawler_args=(), crawler_kwargs={}
    ) -> None:
        self.queue = deque(start_urls)
        self.history = set()
        self.data_pipeline = data_pipeline
        self.num_crawlers = num_crawlers
        self.crawlers = [
            crawler_type(
                queue=self.queue,
                history=self.history,
                data_pipeline=data_pipeline,
                name=name_format.format(i+1),
                *crawler_args, **crawler_kwargs
            )
            for i in range(num_crawlers)
        ]

    def run(self):
        try:
            for crawler in self.crawlers:
                crawler.start()
        except:
            with open("queue.txt", "w") as queue_f, open("history.txt", "w") as hist_f:
                queue_f.writelines(self.queue)
                hist_f.writelines(self.history)
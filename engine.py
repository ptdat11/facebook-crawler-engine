from crawler import Crawler
from pipeline import Pipeline
from progress import Progress
from logger import Logger

from typing import Sequence, Type
import threading

class Engine:
    def __init__(
        self,
        crawler_type: Type[Crawler],
        start_urls: Sequence[str],
        data_pipeline: Pipeline,
        progress_dir: str = "./progress",
        num_crawlers: int = 1,
        name_format: str = "Crawler-{0}",
        crawler_args=(), crawler_kwargs={}
    ) -> None:
        self.logger = Logger("Engine")
        self.progress = Progress(progress_dir)
        for url in set(start_urls).difference(self.progress.queue):
            self.progress.enqueue(url, "left")

        self.termination_event = threading.Event()
        self.data_pipeline = data_pipeline

        self.num_crawlers = num_crawlers
        self.crawlers = [
            crawler_type(
                termination_event=self.termination_event,
                progress=self.progress,
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
            for crawler in self.crawlers:
                crawler.join()
        finally:
            self.termination_event.set()
            self.logger.warn("Saving progress on termination")
            self.progress.save()
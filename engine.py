from crawler import Crawler
from pipeline import Pipeline
from progress import Progress
from logger import Logger

from typing import Sequence, Type
import threading

class Engine:
    """
    The Engine class is responsible for managing a set of crawlers.
    It provides methods to start and wait for crawlers, as well as save progress.
    """
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
        """
        Initializes the Engine with the given crawler type, start URLs, data pipeline, and other parameters.
        
        :param crawler_type: The type of crawler to use.
        :param start_urls: The initial URLs to crawl.
        :param data_pipeline: The pipeline to process crawled data.
        :param progress_dir: The directory to store progress.
        :param num_crawlers: The number of crawlers to run concurrently.
        :param name_format: The format for crawler names.
        :param crawler_args: Additional arguments to pass to crawlers.
        :param crawler_kwargs: Additional keyword arguments to pass to crawlers.
        """
        self.logger = Logger("Engine")
        # Create a logger for the Engine.
        self.progress = Progress(progress_dir)
        # Create a progress tracker.
        for url in (
            set(start_urls)
           .difference(self.progress.queue)
           .difference(self.progress.history)
        ):
            # Enqueue URLs that are not already in progress or history.
            self.progress.enqueue(url, "left")

        self.termination_flag = threading.Event()
        # Create a flag to signal crawler termination.
        self.data_pipeline = data_pipeline
        # Store the data pipeline.

        self.num_crawlers = num_crawlers
        # Store the number of crawlers.
        self.crawlers = [
            crawler_type(
                termination_event=self.termination_flag,
                progress=self.progress,
                data_pipeline=data_pipeline,
                name=name_format.format(i+1),
                *crawler_args, **crawler_kwargs
            )
            for i in range(num_crawlers)
        ]
        # Create a list of crawlers with the given parameters.

    def wait_all(self):
        """
        Waits for all crawlers to finish.
        """
        for crawler in self.crawlers:
            crawler.join()

    def run(self):
        """
        Starts all crawlers and waits for them to finish.
        """
        try:
            for crawler in self.crawlers:
                crawler.start()
            # Start all crawlers.
            self.wait_all()
        except:
            # Catch any exceptions and set the termination flag.
            self.termination_flag.set()
        finally:
            self.wait_all()
            # Ensure all crawlers have finished.
            self.logger.warn("Saving progress on termination")
            # Log a warning message.
            self.progress.save()
            # Save progress.
from collections import deque
import os
import pathlib

from typing import Literal

class Progress:
    def __init__(
        self,
        dir_path: str = "./progress"
    ) -> None:
        dir = pathlib.Path(dir_path)
        self.progress_dir = dir
        self.history_path = dir.joinpath("history.txt")
        self.queue_path = dir.joinpath("queue.txt")

        self.history, self.queue = self.load()
    
    def load(self):
        # Prepare history
        if not self.history_path.exists():
            history = []
        else:
            with open(self.history_path, "r") as f_hist:
                history = f_hist.read().split()

        # Prepare queue
        if not self.queue_path.exists():
            queue = deque()
        else:
            with open(self.queue_path, "r") as f_queue:
                queue = f_queue.read().split()

        return set(history), deque(queue)
    
    def save(self):
        if not self.progress_dir.is_dir():
            os.makedirs(self.progress_dir, exist_ok=True)

        with open(self.history_path, "w") as f_hist, open(self.queue_path, "w") as f_queue:
            f_hist.writelines("\n".join(self.history))
            f_queue.writelines("\n".join(self.queue))

    def enqueue(self, url: str, side: Literal["left", "right"] = "right"):
        if side == "right":
            self.queue.append(url)
        elif side == "left":
            self.queue.appendleft(url)
    
    def next_url(self, pop: bool = True):
        if pop:
            return self.queue.popleft()
        return self.queue[0]

    def add_history(self, url: str):
        self.history.add(url)
    
    def propagated(self, url: str):
        return url in self.history

    def remaining_num(self):
        return len(self.queue)
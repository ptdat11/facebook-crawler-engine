from pandas import DataFrame
from typing import Sequence, Callable, Any
import os


class Pipeline:
    def __init__(
        self,
        *steps: Callable[[Any], Any]
    ) -> None:
        self.steps = [*steps]
    
    def __call__(
        self,
        input: Any
    ) -> Any:
        result = input
        for step in self.steps:
            result = step(input)
        return result
    
    def add(self, step: Callable[[Any], Any]):
        self.steps.append(step)


class SaveAsCSV:
    def __init__(
        self,
        path: str,
        columns: Sequence[str],
    ) -> None:
        self.path = path
        self.columns = columns

    def __call__(
        self,
        data: Any
    ) -> Any:
        df = DataFrame(data, columns=self.columns)
        df.to_csv(
            self.path,
            index=False,
            mode="a",
            header=not os.path.exists(self.path)
        )

        return data
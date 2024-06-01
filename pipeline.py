from selenium import webdriver
from pandas import DataFrame
from typing import Sequence, Callable, Any
import os
import pathlib
import requests

class Pipeline:
    def __init__(
        self,
        *steps: Callable[[Any], Any]
    ) -> None:
        self.steps = [
            AsDataFrame(), 
            *steps
        ]
    
    def __call__(
        self,
        input: Any
    ) -> Any:
        result = input
        for step in self.steps:
            result = step(result)
        return result
    
    def add(self, step: Callable[[Any], Any]):
        self.steps.append(step)


class AsDataFrame:
    def __call__(self, data: dict[str, Any]) -> Any:
        if not isinstance(data, Sequence):
            data = [data]
        df = DataFrame(data)
        return df


class SaveImages:
    def __init__(
        self,
        save_dir: str,
        img_col: str = "images",
        img_name_format: str = "{post_id}_{cmt_id}_{ordinal}.jpg",
        replace_url_with_file_name: bool = True
    ) -> None:
        self.img_col = img_col
        self.save_dir = pathlib.Path(save_dir)
        self.img_name_format = img_name_format
        self.replace_url = replace_url_with_file_name

        if not self.save_dir.exists():
            os.makedirs(self.save_dir, exist_ok=True)
    
    def save_img(
        self,
        url: str,
        post_id: str,
        cmt_id: str,
        ordinal: int
    ):
        img_name = self.img_name_format.format(
            post_id=post_id,
            cmt_id=cmt_id,
            ordinal=ordinal
        )
        img_path = self.save_dir / img_name
        img_data = requests.get(url).content
        with open(img_path, "wb") as f:
            f.write(img_data)
        return img_name

    def __call__(
        self, 
        df: DataFrame,
    ) -> Any:
        for tp in df.itertuples():
            img_files = []
            imgs = tp.images.split()
            for i, url in enumerate(imgs):
                img_file = self.save_img(
                    url=url,
                    post_id=tp.post_id,
                    cmt_id=tp.cmt_id,
                    ordinal=i
                )
                img_files.append(img_file)
            if self.replace_url:
                df.loc[tp.Index, "images"] = " ".join(img_files)
        
        return df
        

class SaveAsCSV:
    def __init__(
        self,
        path: str,
    ) -> None:
        self.path = pathlib.Path(path)
        if not self.path.parent:
            os.makedirs(self.path.parent, exist_ok=True)

    def __call__(
        self,
        df: DataFrame
    ) -> Any:

        df.to_csv(
            self.path,
            index=False,
            mode="a",
            header=not os.path.exists(self.path)
        )

        return df
import pickle
import pathlib
import os

class FacebookCookies:
    def __init__(
        self,
        dir_path: str = "./fb-cookies"
    ) -> None:
        dir = pathlib.Path(dir_path)
        self.dir_path = dir
        self.cookies_path = self.dir_path.joinpath("cookies.pkl")
    
    def save(self, cookies: list[dict]):
        if not self.dir_path.is_dir():
            os.mkdir(self.dir_path)
        
        with open(self.cookies_path, "wb") as f:
            pickle.dump(cookies, f)
    
    def load(self):
        if not self.cookies_path.exists():
            return []
        
        with open(self.cookies_path, "rb") as f:
            cookies = pickle.load(f)
            return cookies
    
    def exists(self):
        return self.cookies_path.exists()
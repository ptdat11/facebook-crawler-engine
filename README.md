# Crawler Engine for Facebook

## How to run Engine

In the `crawler.py` file, go to line no.63. Replace your driver link suitable with your current Google Chrome version in your machine. The links can be found at: [https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/)

In the `main.py` file:

1. Provide the page IDs your would scrape
2. From your CLI, run:

```sh
python3 main.py
```

> Recommended number of crawlers: **2** (ie. 2 pages by default in `main.py`)

> Recommended number of comment loading times: As **small** as possible (Scraping comments highly increases the chance of being blocked by Facebook)

## How to save Cookies to keep the login session?

There is a `save-cookies.ipynb` providing a step-by-step guide in order to store cookies in a local directory.

## Engine Requirements

1. Set your Facebook default language as Vietnamese.
2. Disable auto-translation in your Facebook settings.
3. (Optional) Connection to a strong network.

## Engine Architecture

![Engine architecture](https://github.com/ptdat11/facebook-crawler-engine/blob/main/architecture.png?raw=true)

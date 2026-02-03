# star_scraper.py
import os
import re
import warnings
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Union

from json import dump
from amazoncaptcha import AmazonCaptcha
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

warnings.filterwarnings("ignore")

RATING_PERCENTAGE_PATTERN = re.compile(r"(\d+)\s+stars represent (\d+)% of rating")


class Browser:

    def __init__(self, page_load_timeout: int, headless: bool) -> None:
        self._browser = self.set_browser(page_load_timeout, headless)

    @staticmethod
    def set_browser(page_load_timeout: int, headless: bool) -> WebDriver:
        options = Options()
        options.headless = headless
        options.add_experimental_option("detach", True)
        options.add_argument("--incognito")
        browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        browser.maximize_window()
        browser.set_page_load_timeout(page_load_timeout)
        return browser

    def redirect(self, url: str) -> None:
        self._browser.execute_script(f"window.location.href = '{url}';")

    def open_new_tab(self, url: str) -> None:
        self._browser.execute_script(f"window.open('{url}');")

    def current_browser(self) -> WebDriver:
        return self._browser

    def switch_tab(self, tab_window_handle: str) -> None:
        if self._browser.current_window_handle != tab_window_handle:
            self._browser.switch_to.window(tab_window_handle)

    def all_tabs(self) -> list[str]:
        return self._browser.window_handles

    def close(self, tab_id: Union[int, None] = None) -> None:
        tabs = self.all_tabs()
        if tabs:
            if tab_id is None:
                self._browser.close()
            else:
                if tab_id < len(tabs):
                    self.switch_tab(tabs[tab_id])
                    self._browser.close()
                else:
                    raise ValueError(
                        f"Wrong tab id given,\nMaximum allow 'tab_id' is {len(tabs)}"
                    )

    def __del__(self) -> None:
        tabs = self.all_tabs()
        for tab in tabs:
            self.switch_tab(tab)
            self._browser.close()


class AmazonScraper:

    # def __init__(
    #     self, asin: str, sky_number:str, page_load_timeout: int = 10, headless: bool = False
    # ) -> None:
    def __init__(
        self, asin: str, page_load_timeout: int = 10, headless: bool = False
    ) -> None:
        self.amazon_browser = Browser(
            page_load_timeout=page_load_timeout, headless=headless
        )
        self.asin = asin
        # self.sky_number = sky_number
        self.sign_in_url = "https://www.amazon.in/-/hi/ap/signin?openid.pape.max_auth_age=3600&openid.return_to=https%3A%2F%2Fwww.amazon.in%2Fspr%2Freturns%2Fgift&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=amzn_psr_desktop_in&openid.mode=checkid_setup&language=en_IN&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
        self.product_url = f"https://www.amazon.com/gp/product/{self.asin}"
        self.review_url = f"https://www.amazon.com/product-reviews/{self.asin}/?pageNumber=page_no&filterByStar=no_of_star_ratings"

    @staticmethod
    def bypass_captcha(browser, url: str) -> None:
        browser.get(url)
        try:
            link = browser.find_element(
                By.XPATH, "//div[@class = 'a-row a-text-center']//img"
            ).get_attribute("src")
        except:
            pass
        else:
            captcha = AmazonCaptcha.fromlink(link)
            captcha_value = AmazonCaptcha.solve(captcha)
            browser.find_element(By.ID, "captchacharacters").send_keys(captcha_value)
            button = browser.find_element(By.CLASS_NAME, "a-button-text")
            button.click()

    def sign_in(self) -> None:
        current_browser = self.amazon_browser.current_browser()
        self.bypass_captcha(current_browser, self.sign_in_url)
        email = os.getenv("EMAIL")
        pwd = os.getenv("PWD")
        try:
            current_browser.find_element(By.ID, "ap_email").send_keys(email)
            current_browser.find_element(By.ID, "ap_password").send_keys(pwd)
            button = current_browser.find_element(By.ID, "signInSubmit")
            button.click()
        except:
            pass

    def scrap_reviews(self):
        reviews_data = {}

        def get_reviews_data(page_source):
            soup = BeautifulSoup(page_source, "html.parser")
            reviews = soup.findAll("div", {"data-hook": "review"})
            if reviews:
                for item in reviews:
                    if "product title" not in reviews_data.keys():
                        reviews_data["product title"] = soup.title.text.replace(
                            "Amazon.com: Customer reviews: ", ""
                        ).strip()
                        reviews_data["overall rating"] = soup.find(
                            "span", {"data-hook": "rating-out-of-text"}
                        ).text.strip()
                        reviews_data["total ratings"] = (
                            soup.find("div", {"data-hook": "total-review-count"})
                            .find("span", {"class": "a-size-base a-color-secondary"})
                            .text.strip()
                            .replace(" global ratings", "")
                        )
                        rating = soup.findAll(
                            "tr", {"class": "a-histogram-row a-align-center"}
                        )
                        rating_percentages = {}
                        for r in rating:
                            match = RATING_PERCENTAGE_PATTERN.search(
                                r.get("aria-label")
                            )
                            if match:
                                stars = int(match.group(1))
                                percentage = int(match.group(2))
                                rating_percentages[stars] = percentage
                        reviews_data["rating percentages"] = rating_percentages

                    try:
                        review = {
                            "title": "\n".join(
                                item.find(
                                    "a", {"data-hook": "review-title"}
                                ).text.split("\n")[1:]
                            ).strip(),
                            "rating": item.find(
                                "i", {"data-hook": "review-star-rating"}
                            ).text.strip(),
                            "body": item.find(
                                "span", {"data-hook": "review-body"}
                            ).text.strip(),
                        }
                    except Exception as e:
                        print(self.asin, e)
                    else:
                        if "reviews" not in reviews_data.keys():
                            reviews_data["reviews"] = [review]
                        else:
                            reviews_data["reviews"].append(review)
                return True
            else:
                return False

        star_list = ["one_star", "two_star", "three_star"]
        for star in star_list:
            i = 1
            while True:
                review_page_url = self.review_url.replace("page_no", f"{i}").replace(
                    "no_of_star_ratings", star
                )
                current_browser = self.amazon_browser.current_browser()
                self.bypass_captcha(current_browser, review_page_url)
                reviews_present = get_reviews_data(current_browser.page_source)
                if reviews_present:
                    i += 1
                    continue
                else:
                    break
        # print(reviews_data)
        # try:
        #     print('In_nextpage')
        #     next_page_url = current_browser.find_element(By.LINK_TEXT, 'Next page').get_attribute("href")
        #     print('In_nextpage2')
        #     print(f"Next page--------{next_page_url}")
        #     self.bypass_captcha(current_browser, next_page_url)
        #     get_reviews_data(next_page_url)
        # except NoSuchElementException:
        #     break
        # else:
        #     self.amazon_browser.redirect(next_page_url)
        return reviews_data

    def scrap_product_info(self, is_captcha_bypass: bool = True) -> dict:
        current_browser = self.amazon_browser.current_browser()
        if is_captcha_bypass:
            self.amazon_browser.redirect(self.product_url)
        else:
            self.bypass_captcha(current_browser, self.product_url)
        soup = BeautifulSoup(current_browser.page_source, "html.parser")
        info = {}

        try:
            price = soup.find(
                "span", attrs={"id": "priceblock_ourprice"}
            ).string.strip()
        except AttributeError:
            price = "NA"
        info["price"] = price

        try:
            product_info_list = soup.find(
                "ul", class_="a-unordered-list a-vertical a-spacing-mini"
            ).find_all("li", class_="a-spacing-mini")
            product_info = [p.span.text.strip() for p in product_info_list]
        except AttributeError:
            product_info = []
        info["details"] = product_info

        try:
            table = soup.find("table", {"id": "productDetails_detailBullets_sections1"})
            if table:
                table_rows = table.find("tbody").findAll("tr")
                bsr = ""
                for tr in table_rows:
                    text = tr.text
                    if "Best Sellers Rank" in text:
                        bsr = text.replace("Best Sellers Rank", "").strip()
                        break
                bsr = bsr.split("#")
                bsr = [b.strip() for b in bsr if b.strip()]
            else:
                bsr = []
        except AttributeError:
            bsr = []
        info["best seller rank"] = bsr

        return info

    def write_json(self, data: dict, json_path: str) -> None:
        with open(json_path, "w") as json_file:
            dump(data, json_file, indent=4)

    def __call__(self) -> dict:
        reviews = self.scrap_reviews()
        info = self.scrap_product_info()
        # scrap_data = {**reviews, **info, "asin":self.asin, "sky":self.sky_number}
        scrap_data = {**reviews, **info, "asin":self.asin}
        # self.write_json(
        #     scrap_data, (os.path.join("./product_data", f"{self.asin}.json"))
        # )
        return scrap_data

    def __del__(self) -> None:
        del self.amazon_browser


# def scrap_from_amazon(asin_number: str, sky_number: str):
#     scraper = AmazonScraper(asin=asin_number, sky_number=sky_number)
def scrap_from_amazon(asin_number: str):
    scraper = AmazonScraper(asin=asin_number)
    scrap_data = scraper()
    del scraper
    return scrap_data


if __name__ == "__main__":
    asins = [
        "B0C88FHVFV"
    ]
    # with ThreadPoolExecutor(max_workers=2) as executor:
    #     futures = [executor.submit(scrap_from_amazon, no) for no in asins]
    #     wait(futures)
    #     results = [f.result() for f in futures]
    # print(results)
    for asin in asins:
        print(asin)
        scrap_from_amazon(asin, sky_number="SKY6966")

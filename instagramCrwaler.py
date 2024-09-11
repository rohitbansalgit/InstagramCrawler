import time
import pickle
from selenium import webdriver
from selenium.common import StaleElementReferenceException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import googlespreadsheet
import requests
import re
import db
import sys


class InstagramLoginWithCookies:
    def __init__(self):
        self.driver = None
        self.insta_user_details = {
            "bio_link": {},  # Initialize bio_link as an empty 0list
            "bio_link_details": {},  # Initialize bio_link as an empty 0list
        }
        self.head_profile_name = ""
        self.head_profile_url = ""
        self.PARENT_HEADER = False
        self.PROFILE_SCRAPED = 0
        self.HEADER_APPEND = False

    def setup_driver(self):
        # Set up the Chrome driver
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new")  # Run Chrome in headless mode
        # chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
        # chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )  # Add user agent

        self.driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options,
        )

        self.driver.maximize_window()

    def load_cookies_and_login(self):
        self.driver.get("https://www.instagram.com/")

        time.sleep(3)  # wait for the page to load

        # Load cookies from file
        with open("instagram_cookies.py", "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

        self.driver.refresh()
        time.sleep(5)  # wait for the page to load with the cookies
        # check HTTP ERROR 429 code if 429 then wait for 5 minutes

    def scroll_page(self, scroll_amount=1000):
        # Scroll down the page by the specified amount
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")

    def keep_browser_open(self):
        print("Browser will remain open indefinitely. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")

    def click_turn_on_notifications(self):
        time.sleep(1)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        self.find_span_and_click_button(soup)

    def find_search_button(self):
        a_tags = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a._a6hd"))
        )

        urls = [a.get_attribute("href") for a in a_tags]

        # Print the list of URLs
        i = 0
        for url in urls:
            if "direct/inbox" in url:
                break
            i = i + 1
        i = i - 3
        # Iterate through the elements and perform actions
        j = 0
        for atag in a_tags:
            if j == i:
                time.sleep(2)
                atag.click()
            j = j + 1
        return True

    def count_occurrences_with_regex(self, text, sub_str):
        matches = re.findall(sub_str, text)
        return len(matches)

    def find_span_and_click_button(self, soup):
        # Find the span containing the substring 'Turn on Notifications'
        row_notification_txt = soup.text.replace("\n", "").replace("\r", "")
        is_notification_text_N = self.count_occurrences_with_regex(
            row_notification_txt, "Turn on Notifications"
        )
        is_notification_text_n = self.count_occurrences_with_regex(
            row_notification_txt, "Turn on notifications"
        )
        if is_notification_text_N > 0 or is_notification_text_n > 0:
            # print("Span with 'Turn on Notifications' found")
            button = self.driver.find_element(By.CLASS_NAME, "_a9_0")
            if button:
                # print("Button found")
                # Click the button
                button.click()

                self.find_search_button()
                for row_no in range(10):
                    if (
                        row_no > 0
                    ):  # skip first row because first time follower popup will not available
                        follower_popup_close = self.driver.find_element(
                            By.CSS_SELECTOR, "button._abl-"
                        )
                        if follower_popup_close:
                            follower_popup_close.click()
                            time.sleep(2)
                            self.find_search_button()

                    name = googlespreadsheet.get_name_from_googlesheet(row_no + 1)
                    if len(name) > 0 and len(name[0]) > 0:
                        try:
                            self.find_name_in_search(
                                name[0][0]
                            )  # only got single name at a time in list so always [0][0]
                            self.head_profile_name = name[0][
                                0
                            ]  # only got single name at a time in list so always [0][0]

                        except Exception:
                            print(
                                "An error occurred while processing the Instagram data."
                            )
                    else:
                        print("All data processed")
                        break
        else:
            is_429_error = self.count_occurrences_with_regex(
                row_notification_txt, "HTTP ERROR 429"
            )
            if is_429_error > 0:
                print(
                    "HTTP ERROR 429, Need to switch Instagram account with remove browser cache"
                )
                sys.exit()
            else:
                print("Span with 'Turn on Notifications' not found")

    def get_all_work_inner_div(self, div, start=None):
        time.sleep(5)
        inner_div_elements = div.find_elements(
            By.CSS_SELECTOR, "div.xl56j7k.xeuugli"
        )  # find inner divs in followers popup, this div contains profile url
        i = 1
        j = 1
        for inner_div in inner_div_elements:  # iterate through the all profile on popup
            if start is not None and i < start:
                i = i + 1
                continue
            if self.check_anchor_tag_in_bio(
                inner_div
            ):  # check for clickable anchor tag of profile, in popup
                anchor = self.check_anchor_tag_in_bio(inner_div)
                j = j + 1
                href = anchor.get_attribute("href")
                print(href)
                self.PROFILE_SCRAPED = self.PROFILE_SCRAPED + 1
                print(f"Profile checked till now: {self.PROFILE_SCRAPED}")
                if href:
                    check_data_exists = db.MongoDBClient().is_data_exists(
                        {"profile_url": href}
                    )
                    if check_data_exists:
                        print("Data already exists")
                        continue
                self.insta_user_details["bio_link_details"] = {}
                self.insta_user_details["bio_link"] = {}
                self.open_follower_new_tab(
                    anchor
                )  # click on profile link in popup and open in new tab
                descriprtion_bio = self.get_bio_data(
                    True
                )  # get bio data available on profile page
                DATA_APPEND = False
                if descriprtion_bio:
                    self.get_bio_links_on_bio_description(descriprtion_bio, True)
                    self.get_external_link_bio_popup(descriprtion_bio, True)
                    if len(self.insta_user_details["bio_link"]) > 0:
                        self.send_data_for_save()
                        DATA_APPEND = True
                if not DATA_APPEND:
                    # save data to db
                    try:
                        db.MongoDBClient().insert_document(self.insta_user_details)
                    except:
                        print("Error saving data to db")

    def scroll_popup_until_no_more_data(
        self, driver, div, end_data_on_popup, scroll_pause_time=3
    ):
        popup = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.x1rife3k"))
        )

        return popup

    def check_anchor_tag_in_bio(self, inner_div):
        try:
            anchor = inner_div.find_element(By.CSS_SELECTOR, "a._a6hd")
            if anchor:
                return anchor
            else:
                return False
        except Exception:
            print("anchor tag in bio not found")
            return False

    def click_follow_button(self):
        try:
            follow_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.x9n4tj2._a6hd"))
            )
            if follow_link:
                # print("follow link found")
                time.sleep(1)
                try:
                    follow_link.click()
                except Exception:
                    print("follow link not found")
                    # sys.exit()
                    return False
                return True

            else:
                print("follow link not found")
                # sys.exit()
                return False
        except Exception:
            return False

    def find_name_in_search(self, name):

        search_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.x7xwk5j"))
        )
        if search_input:
            # print("Search input found")
            # Enter the search term
            search_input.send_keys(name)
            # Submit the search form
            search_input.send_keys(Keys.RETURN)
            # print("Search term entered and form submitted")
            time.sleep(3)

            name_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "a.x193iq5w.xh8yej3")
                )
            )
            if name_list:
                # print("Name list found")
                print(name_list[1].text)
                time.sleep(2)
                name_list[1].click()
                # print("Name clicked")
                time.sleep(4)
                return True
            else:
                # print("In search, name list not found")
                return False
        else:
            # print("Search input not found")
            return False

    def open_follower_new_tab(self, anchor):
        anchor.send_keys(Keys.CONTROL + Keys.RETURN)
        # Switch to the new tab
        self.driver.switch_to.window(self.driver.window_handles[1])
        # Wait for the page to load
        time.sleep(5)
        return True

    def get_insta_id_and_name(self, parent=None):
        time.sleep(5)
        current_url = self.driver.current_url

        try:
            insta_id = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "h2.x1ms8i2q.xo1l8bm.x5n08af.x10wh9bi.x1wdrske.x8viiok.x18hxmgj",
                    )
                )
            )

            if parent == "parent":
                self.head_profile_url = current_url
            # print(insta_id.text)
            # Get the Instagram ID
            self.insta_user_details["insta_id"] = insta_id.text
        except Exception:
            pass
            # print("Insta id and name not found")

        # Get the Instagram profile URL
        self.insta_user_details["profile_url"] = current_url

    def get_bio_data(self, parent=None):
        self.get_insta_id_and_name(parent)

        insta_bio = self.driver.find_element(
            By.CSS_SELECTOR, "section.x16zxmhm.x6ikm8r.x10wlt62"
        )
        # link can be in anchor tag or button tag
        if insta_bio:
            self.insta_user_details["insta_bio"] = insta_bio.text
        else:
            self.insta_user_details["insta_bio"] = "No bio found"
        return insta_bio

    def get_bio_links_on_bio_description(self, insta_bio, parent=None):
        anchor_tags = insta_bio.find_elements(By.TAG_NAME, "a")

        if anchor_tags:
            try:
                WebDriverWait(insta_bio, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
                urls = [a.get_attribute("href") for a in anchor_tags]
                if urls:
                    self.save_external_link_data(urls, parent, False)
                    return True
                else:
                    # print("Link found in bio but not able to get it")
                    return False
            except Exception:
                pass
                # print(f"Error finding bio link, bio link not found")
        else:
            # print("No link found in bio")
            self.insta_user_details["bio_link"] = {}
            return False

    def get_external_link_bio_popup(self, insta_bio, parent=None):
        try:
            button_tags = insta_bio.find_elements(By.TAG_NAME, "button")
        except Exception:
            # print("bio link popup button not found")
            return False

        if len(button_tags) > 0:  # When bio link has popup button
            try:
                WebDriverWait(insta_bio, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "button"))
                )
                bio_popup_link_button = insta_bio.find_element(By.TAG_NAME, "button")
                bio_popup_link_button.click()
                # print("Bio link popup button clicked")
                time.sleep(5)
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.xzkaem6"))
                    )
                    bio_link_popup = self.driver.find_element(
                        By.CSS_SELECTOR, "div.xzkaem6"
                    )
                    # print("Bio link popup opened")
                    popup_anchor_tags = bio_link_popup.find_elements(By.TAG_NAME, "a")
                    if (
                        len(popup_anchor_tags) > 0
                    ):  # When on bio button popup, anchor tags found
                        # print("Link found in bio popup")
                        urls = self.get_bio_links_from_popup(
                            bio_link_popup, parent, True
                        )
                        if len(urls) > 0:
                            self.save_external_link_data(urls, parent, True)
                        try:
                            popup_close = bio_link_popup.find_element(
                                By.CSS_SELECTOR, "div.xurb0ha.xcdnw81"
                            )
                            popup_close.click()
                            time.sleep(1)
                            self.close_current_tab()
                        except Exception:
                            pass
                            # print("Error closing bio link popup")
                    else:
                        # print("No link found in bio popup")
                        self.close_current_tab(parent)
                except Exception:
                    pass
                    # print("Error finding bio link popup")
            except Exception:
                pass
                # print("Error clicking bio link popup button")
        else:
            # print("No popup button found in bio")
            try:
                self.close_current_tab(parent)
            except Exception:
                pass
                # print("Error closing bio link popup")

    def get_bio_links_from_popup(self, popup_element, parent=None, is_popup=False):
        try:
            a_tags = WebDriverWait(popup_element, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            urls = []
            if a_tags:
                urls = [a.get_attribute("href") for a in a_tags]

            if len(urls) > 0:
                return urls
            else:
                # print("No link found in bio pop up")
                time.sleep(2)
                self.close_current_tab(parent)
        except Exception:
            pass
            # print("Error finding bio links in popup")
        return True

    def save_external_link_data(self, urls, parent=None, is_popup=False):
        i = len(self.insta_user_details["bio_link_details"])

        for url in urls:
            excluded_keywords = [
                "threads.net",
                "facebook.com",
                "youtube.com",
                "www.instagram.com",
                "tiktok.com",
                "depop.com",
                "/x.com",
                "twitter.com",
                "google.com",
                "pinterest.com",
                "linkedin.com",
                "snapchat.com",
                "reddit.com",
                "tumblr.com",
                "explore/tags",
                "/followers/",
            ]

            is_insta = self.not_contains_instagram_url(url)
            if any(keyword in url for keyword in excluded_keywords):
                continue
            else:
                # self.insta_user_details['bio_link'][i] = url
                if self.is_page_response_200(url):
                    self.driver.execute_script(f"window.open('{url}', '_blank');")
                    time.sleep(5)
                    no_of_tabs = len(self.driver.window_handles) - 1
                    # Switch to the new tab
                    self.driver.switch_to.window(self.driver.window_handles[no_of_tabs])
                    time.sleep(5)
                    # Get the external page data
                    if self.find_fans_com_in_html(self.driver):
                        self.insta_user_details["bio_link"][i] = url
                        self.insta_user_details["bio_link_details"][i] = (
                            self.get_link_name(self.driver)
                        )
                        i = i + 1
                    self.close_current_tab(parent, is_popup)
                    # print(f"External link found: {url}")

    def not_contains_instagram_url(self, url):
        pattern = r"l\.instagram\.com"
        return bool(re.search(pattern, url))

    def find_fans_com_in_html(self, driver):
        html_content = driver.page_source
        return bool(match)

    def get_link_name(self, driver):
        html_content = driver.page_source

        return "Found google.com"

    def is_page_response_200(self, url):
        try:
            response = requests.get(url)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False

    def send_data_for_save(self):
        print(self.insta_user_details)
        if self.PARENT_HEADER:
            data = self.add_data_for_parent_google_sheet()
            googlespreadsheet.append_data_to_google_sheet(data)
            # add data to db
            db.MongoDBClient().insert_document(self.insta_user_details)
            self.PARENT_HEADER = False
            print("Parent data saved to google sheet")
        data = self.prepare_data_for_google_sheet(self.insta_user_details)
        if len(data) > 0:
            googlespreadsheet.append_data_to_google_sheet(data)
            db.MongoDBClient().insert_document(self.insta_user_details)
        print("Data appedled to google sheet")

    def prepare_data_for_google_sheet(self, insta_user_details):
        data = []
        row_data = [
            insta_user_details["insta_id"],
            insta_user_details["profile_url"],
            insta_user_details["insta_bio"],
        ]

        for i in range(
            min(
                len(insta_user_details["bio_link"]),
                len(insta_user_details["bio_link_details"]),
            )
        ):
            row_data.append(insta_user_details["bio_link"][i])
            row_data.append(insta_user_details["bio_link_details"][i])
        data.append(row_data)
        return data

    def add_data_for_parent_google_sheet(self):
        data = [[]]
        profile_name = ["Profile Name", self.head_profile_name]
        profile_url = ["Profile URL", self.head_profile_url]
        data.append(profile_name)
        data.append(profile_url)
        data.append([])
        data.append(["Followers Details"])
        data.append(
            [
                "Follower Name",
                "Url",
                "Bio data",
                "Bio link 1",
                "Raw Data on link 1",
                "Bio link 2",
                "Raw Data on link 2",
            ]
        )
        return data

    def close_current_tab(self, parent=None, is_popup=False):
        total_tabs = len(self.driver.window_handles) - 1
        if is_popup:
            self.driver.switch_to.window(self.driver.window_handles[total_tabs])
            self.driver.close()
            time.sleep(2)
        if not is_popup:
            for i in range(total_tabs, 0, -1):
                if i != 0:
                    self.driver.switch_to.window(self.driver.window_handles[i])
                    self.driver.close()
                    time.sleep(2)

        if is_popup:
            self.driver.switch_to.window(self.driver.window_handles[total_tabs - 1])
        else:
            self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(1)
        return True

    def click_button(self, button):
        # Simulate a button click
        print(f"Button with text '{button.text}' clicked.")

    def find_parent_tag(self, driver, tag_name, attribute_name, attribute_value):
        try:
            # Locate the tag using the provided tag name, attribute name, and attribute value
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="mount_0_0_yV"]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[2]/span/div/a',
                    )
                )
            )
            parent_tag = element.find_element(By.XPATH, "..")
            return parent_tag.tag_name
        except Exception:
            # print("Error finding parent tag")
            return None

    def find_text_and_click(self, driver, tag_name, text_to_find):
        try:
            # Locate the tag containing the specified text
            tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//{tag_name}[contains(text(), '{text_to_find}')]")
                )
            )
            # Check if the tag contains the specified text and click it
            if tag and text_to_find in tag.text:
                tag.click()
                return True
        except Exception:
            pass
            # print("Error finding or clicking text in tag:")
        return False


if __name__ == "__main__":
    instagram = InstagramLoginWithCookies()
    instagram.setup_driver()
    instagram.load_cookies_and_login()
    instagram.click_turn_on_notifications()

import logbook
import time
import re
import sys
import configparser
import os
import socket
import pickle

from db.NewsparserDatabaseHandler import NewsparserDatabaseHandler
from Lib.NewsHelper import Helper

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOption
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains


class NewsParserData(object):
    logger = None
    config = None
    driver = None
    cookies = None
    URL = "https://www.straitstimes.com/"

    def __init__(self, db, path_to_webdriver, config=None, logger=None, cookies=None):
        self.logger = logger
        self.logger.info("webdriver path: ".format(path_to_webdriver))

        self.config = config

        # self.cookies_file_path = self.config.get('Selenium', 'cookies_path')

        chrome_options = ChromeOption()

        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        # ignore error proxy
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')

        # automatically dismiss prompt
        chrome_options.set_capability('unhandledPromptBehavior', 'dismiss')

        self.driver = webdriver.Chrome(path_to_webdriver, chrome_options=chrome_options)

        # try:
        #     # load cookies for given websites
        #     cookies = pickle.load(open(self.cookies_file_path, "rb"))
        #     for website in self.URL:
        #         self.driver.get(website)
        #         for cookie in cookies:
        #             self.driver.add_cookie(cookie)
        #         self.driver.refresh()
        # except Exception as e:
        #     # it'll fail for the first time, when cookie file is not present
        #     print(str(e))
        #     print("Error loading cookies")

        self.db = db

    def save_cookies(self):
        # save cookies
        cookies = self.driver.get_cookies()
        pickle.dump(cookies, open(self.cookies_file_path, "wb"))

    def __del__(self):
        # self.save_cookies()
        self.driver.quit()

    def openLink(self, URL):
        self.driver.get(URL)
        self.driver.implicitly_wait(30)
        time.sleep(20)
        # Helper.scroll_down(self.driver)
        # self.logger.info("start get link")

    def openWeb(self):
        self.openLink(self.URL)

        # kalo ada iklan
        try:
            #first iframe
            xads = '//*[@id="google_ads_iframe_/5908/st/prestitial/homepage_0"]'
            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it(self.driver.find_element_by_xpath(xads)))

            #second iframe
            xxads ='//*[@id="2667407632870008044_0-frame"]'
            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it(self.driver.find_element_by_xpath(xxads)))

            button = "//*[@id='pclose-btn']"
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button))).click()

            time.sleep(3)
        except:
            self.logger.info("No Ads, Keep Going!")
        finally:
            self.driver.switch_to.default_content()

    def checkLogin(self):
        xlogin = "//*[@id='sph_login']"

        login = self.driver.find_element_by_xpath(xlogin)

        if login is not None:
            # ActionChains(self.driver).click(on_element=login).perform()
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xlogin))).click()

            time.sleep(3)

            xusername = '//*[@id="IDToken1"]'
            username = self.driver.find_element_by_xpath(xusername)
            username.send_keys('kelvinkoh013@hotmail.com')
            xpassword = '//*[@id="IDToken2"]'
            password = self.driver.find_element_by_xpath(xpassword)
            password.send_keys('Password13')
            password.send_keys(Keys.ENTER)

            time.sleep(20)

    def clickSingapore(self):
        xsingapore = '//*[@id="navbar"]/div/div[2]/nav/ul/li[2]/a'

        singapore = self.driver.find_element_by_xpath(xsingapore)

        singapore.click()

        time.sleep(20)

    def getLink(self):
        xcontainer = '//*[@id="block-system-main"]/div/div/div/div/div[3]/div/div/div/div[3]/div/div/div/div'
        xcontainer2 = '//*[@id="block-system-main"]/div/div/div/div/div[3]/div/div/div/div[5]/div/div/div/div'

        container = self.driver.find_elements_by_xpath(xcontainer)
        container2 = self.driver.find_elements_by_xpath(xcontainer2)

        action_chains = ActionChains(self.driver)
        alink = []

        for i in range(len(container)):
            con = container[i]
            action_chains.move_to_element(con).perform()

            xlink = './/a[1]'
            link = con.find_element_by_xpath(xlink)
            link_ = link.get_attribute('href')
            alink.append(link_)

        for i in alink:
            self.parsingNews(i)

    def getDate(self, input):
        re_date = r"(\d{4}-\d{2}-\d{2}).?(\d{2}:\d{2}:\d{2})"

        date = re.search(re_date, input)
        time = date.group(1) + " " + date.group(2)

        return time

    def parsingNews(self, link):

        self.openLink(link)

        xtitle = './/h1[@class="headline node-title"]'
        title = self.driver.find_element_by_xpath(xtitle)
        title = title.text
        self.logger.info("title : {}".format(title))

        xdate = './/meta[@property="article:published_time"]'
        date = self.driver.find_element_by_xpath(xdate)
        date_ = date.get_attribute("content")

        tanggal = self.getDate(date_)
        self.logger.info("published : {}".format(tanggal))

        xname = './/div[@class="author-field author-name"]'
        name = self.driver.find_elements_by_xpath(xname)

        xcontent = './/p'
        content = self.driver.find_elements_by_xpath(xcontent)

        editor = ""
        for i in range(len(name)):
            editor += name[i].text
        self.logger.info("editor : {}".format(editor))

        content_ = ""
        for i in range(len(content)):
            content_ += content[i].text
        self.logger.info("content : {}".format(content_))

        self.db.insert_news(title, content_, tanggal, editor, link)

    def logoutAcc(self):
        # click account
        xacc = './/a[@name="login-user-name"]'

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xacc))).click()

        # click logout
        xlogout = './/a[@class="mysph_logout"]'

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xlogout))).click()

        time.sleep(20)


class NewsParsing(object):
    config = None
    logger = None
    filename = ""
    iphelper = None
    db = None
    hostname = ''
    hostip = ''

    def init(self):

        self.filename, file_extension = os.path.splitext(os.path.basename(__file__))
        config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../config', 'config.ini')
        log_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../logs', '%s.log' % self.filename)

        # load config
        self.config = configparser.ConfigParser(strict=False, allow_no_value=True)
        self.config.read(config_file)

        # init logger
        logbook.set_datetime_format("local")
        self.logger = logbook.Logger(name=self.filename)
        format_string = '%s %s' % ('[{record.time:%Y-%m-%d %H:%M:%S.%f%z}] {record.level_name}',
                                   '{record.channel}:{record.lineno}: {record.message}')
        if self.config.has_option('handler_stream_handler', 'verbose'):
            loghandler = logbook.StreamHandler(sys.stdout, level=self.config.get('Logger', 'level'), bubble=True,
                                               format_string=format_string)
            self.logger.handlers.append(loghandler)
            loghandler = logbook.TimedRotatingFileHandler(log_file, level=self.config.get('Logger', 'level'),
                                                          date_format='%Y%m%d', backup_count=5, bubble=True,
                                                          format_string=format_string)
            self.logger.handlers.append(loghandler)
        else:
            loghandler = logbook.TimedRotatingFileHandler(log_file, level=self.config.get('Logger', 'level'),
                                                          date_format='%Y%m%d', backup_count=5, bubble=True,
                                                          format_string=format_string)
            self.logger.handlers.append(loghandler)
        self.db = NewsparserDatabaseHandler.instantiate_from_configparser(self.config, self.logger)

    def run(self):
        # start_time = time.time()
        self.init()
        self.hostname = socket.gethostname()
        self.hostip = socket.gethostbyname(self.hostname)
        self.logger.info("Starting {} on {}".format(type(self).__name__, self.hostname))
        self.newsParserData = NewsParserData(db=self.db, path_to_webdriver=self.config.get('Selenium', 'chromedriver_path'),
                                             config=self.config, logger=self.logger)

        # error handling agar tidak dalam posisi login saat error
        try:
            self.newsParserData.openWeb()
            self.newsParserData.checkLogin()
            self.newsParserData.clickSingapore()
            self.newsParserData.getLink()
        finally:
            self.newsParserData.logoutAcc()

        self.logger.info("Finish %s" % self.filename)
        # print("--- %s seconds ---" % (time.time() - start_time))

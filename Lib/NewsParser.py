import logbook
import time
import re
import sys
import configparser
import os
import socket

from db.NewsparserDatabaseHandler import NewsparserDatabaseHandler
from Lib.NewsHelper import Helper

from bs4 import BeautifulSoup
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

    def __init__(self, path_to_webdriver, config=None, logger=None, cookies=None):
        self.logger = logger
        self.logger.info("webdriver path: ".format(path_to_webdriver))

        self.config = config

        chrome_options = ChromeOption()

        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        # ignore error proxy
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')

        # automatically dismiss prompt
        chrome_options.set_capability('unhandledPromptBehavior', 'dismiss')

        self.driver = webdriver.Chrome(path_to_webdriver, chrome_options=chrome_options)

        if cookies is None:
            self.cookies = self.driver.get_cookies()
        else:
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.cookies = cookies
        # self.db = db

    def __del__(self):
        self.driver.quit()

    def openLink(self):
        self.driver.get(self.URL)
        self.driver.implicitly_wait(30)
        time.sleep(20)
        #Helper.scroll_down(self.driver)
        # self.logger.info("start get link")

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

            time.sleep(10)

    def openNewsLink(self, url):
        self.driver.get(url)
        self.driver.implicitly_wait(5)
        time.sleep(3)
        Helper.scroll_down(self.driver)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        return soup


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
        # self.db = NewsparserDatabaseHandler.instantiate_from_configparser(self.config, self.logger)


    def run(self):
        # start_time = time.time()
        self.init()
        self.hostname = socket.gethostname()
        self.hostip = socket.gethostbyname(self.hostname)
        self.logger.info("Starting {} on {}".format(type(self).__name__, self.hostname))
        self.newsParserData = NewsParserData(path_to_webdriver=self.config.get('Selenium', 'chromedriver_path'),
                                             config=self.config, logger=self.logger)
        self.newsParserData.openLink()
        self.newsParserData.checkLogin()
        self.logger.info("Finish %s" % self.filename)
        # print("--- %s seconds ---" % (time.time() - start_time))

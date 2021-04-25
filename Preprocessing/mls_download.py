import os
import sys
import requests
import shutil
import copy
import glob
import pandas as pd
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

'''
This script is for scraping housing data from the MLS. You will need MLS credentials to be able to
use this script. The data is updated once a month at the beginning of the month. This script can be 
run automatically every month with a task scheduler and can be used as an initial step of a pipeline.
This data comes from the marketwatch / market stats and isn't actually scraping the data from strata;
these are moreso summary statistics per month from 1996 to present for every municipality in the GTA.
'''




options = webdriver.ChromeOptions()
options.add_experimental_option('prefs', {
"download.default_directory": "C:\\Users\\Michael\\MLS\\MLS_Datasets", #Change default directory for downloads
"download.prompt_for_download": False, #To auto download the file
"download.directory_upgrade": True,
"plugins.always_open_pdf_externally": True #It will not show PDF directly in chrome
})
browser = webdriver.Chrome(os.path.join(sys.path[0], 'chromedriver'),options=options)

def login(username, password, authenticator):
    '''
    This function is to log into the MLS ('https://treb.clareityiam.net/idp/login') using your username, password and authenticator
    INPUTS
    username: str
    password: str
    authenticator: str
    '''
    login_url = 'https://treb.clareityiam.net/idp/login'
    browser.get(login_url)
    username_css = browser.find_element_by_css_selector('#clareity')
    username_css.send_keys(username)
    password_css = browser.find_element_by_css_selector('#pin')
    password_css.send_keys(password)
    authenticator_css = browser.find_element_by_css_selector('#security')
    authenticator_css.send_keys(authenticator)
    browser.find_element_by_css_selector('#loginbtn').click()
    time.sleep(2)

def navigate():
    '''
    This function is to navigate to the marketstats to collect the excel data files
    '''
    browser.get('https://communications.torontomls.net/mlshome/redirect/redirectmarketstats.html')
    time.sleep(1)
    browser.switch_to.frame(browser.find_element_by_tag_name("iframe"))
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#tiles > li:nth-child(2)'))).click()
    time.sleep(1)
    browser.switch_to.frame(browser.find_element_by_tag_name("iframe"))
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Button1 > button'))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Button1 > button'))).click()
    time.sleep(2.4)


def get_data():
    ''' 
    This is the function that does most of the work. 
    1. Goes through the dashboard for each combination of house type and municipality (e.g. Detached, Vaughan)
    2. Exports each file
    3. Moves files in directory of city
    '''
    # get all tags we need for selector
    # get all the home type options
    home_types = ['#HierarchyViewer1_Control > option:nth-child' + '(' + str(i) + ')' for i in range(1,11)]
    geography = '#HierarchyViewer2 > button'
    # get all the municipalities of dufferin (there's only one in this case)
    dufferin = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(1) > span.oc'
    dufferin_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child(1) > label']
    # get all the municipalities of durham
    durham = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(2) > span.oc'
    durham_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,9)]
    # get all the municipalities of halton
    halton = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(3) > span.oc'
    halton_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,5)]
    # get all the municipalities of peel
    peel = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(4) > span.oc'
    peel_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,4)]
    # get all the municipalities of simcoe
    simcoe = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(5) > span.oc'
    simcoe_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,6)]
    # get all the municipalities of toronto
    toronto = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(6) > span.oc'
    toronto_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,36)]
    # get all the municipalities of york
    york = 'body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li:nth-child(7) > span.oc'
    york_children = ['body > div.DashboardPopup.Open > div > div > div > ul > li > ul > li.Expanded > ul > li:nth-child'+ '(' + str(i) + ')'+  '> label' for i in range(1,10)]

    #go to data table
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Button1'))).click()
    time.sleep(3)
    update_btn = '#Update1_Button > button'
    export_btn = '#exportItem'
    ####################################################################
    # Scrape Dufferin
    ####################################################################
    for child in dufferin_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, dufferin))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        time.sleep(1)
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Dufferin') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, dufferin))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, durham))).click() # select
    time.sleep(2)
    ##########################################################################################
    # Scrape Durham
    ##########################################################################################
    for child in durham_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Durham') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, durham))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, halton))).click() # select
    time.sleep(2)
    ##########################################################################################
    # Scrape Halton
    ##########################################################################################
    for child in halton_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Halton') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, halton))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, peel))).click() # select
    time.sleep(2)
    ################################################################################################
    # Scrape Peel
    ################################################################################################
    for child in peel_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Peel') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, peel))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, simcoe))).click() # select
    time.sleep(2)
    ###############################################################################################
    # Scrape Simcoe
    ###############################################################################################
    for child in simcoe_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Simcoe') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, simcoe))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, toronto))).click() # select
    time.sleep(2)
    ####################################################################################################
    # Scrape Toronto
    ####################################################################################################
    for child in toronto_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\Toronto') for f in files]

    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, toronto))).click() # deselect
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, york))).click() # select
    time.sleep(2)
    ###################################################################################################
    # Scrape York
    ###################################################################################################
    for child in york_children:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, geography))).click()
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, child))).click()
        for home_type in home_types:
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, home_type))).click()
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, update_btn))).click()
            time.sleep(10)
            browser.switch_to.default_content()
            browser.switch_to.frame(browser.find_element_by_id("frame1"))
            WebDriverWait(browser, 40).until(EC.element_to_be_clickable((By.CSS_SELECTOR, export_btn))).click()
            browser.switch_to.frame(browser.find_element_by_id("dashboardViewFrame"))
            WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'body > div.DashboardPopup.Open.ExportMode > div > div > div > div.Commands > button.ExportCommand'))).click()
            time.sleep(2)
    files = glob.glob("C:\\Users\\Michael\\MLS\\MLS_Datasets\*xlsx")
    [shutil.move(f, 'C:\\Users\\Michael\\MLS\\MLS_Datasets\\York') for f in files]

if __name__ == "__main__":
    login('******', '****', '******')
    navigate()
    areas = ['Dufferin','Durham','Halton','Peel','Simcoe','Toronto','York']
    [os.makedirs(os.path.join(os.getcwd(),'MLS_Datasets', area)) for area in areas if not os.path.exists(os.path.join(os.getcwd(),'MLS_Datasets', area))]
    get_data()

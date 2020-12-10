from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
import time
from tqdm import tqdm
from numpy.random import uniform
from bs4 import BeautifulSoup
import pandas as pd
import re
import ast
import numpy as np
import simpleaudio as sa

from urls import districs_url

MAX_NUMBER_PAGES = 54
ADS_ON_PAGE = 28
PATH_DATA = 'spb_project_data.csv'
TIME_TO_SOLVE = 120

def play_signal():
    frequency = 440  # Our played note will be 440 Hz
    fs = 44100  # 44100 samples per second
    seconds = 2  # Note duration of 3 seconds
    
    # Generate array with seconds*sample_rate steps, ranging between 0 and seconds
    t = np.linspace(0, seconds, seconds * fs, False)
    
    # Generate a 440 Hz sine wave
    note = np.sin(frequency * t * 2 * np.pi)
    
    # Ensure that highest value is in 16-bit range
    audio = note * (2**15 - 1) / np.max(np.abs(note))
    # Convert to 16-bit data
    audio = audio.astype(np.int16)
    
    # Start playback
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    
    # Wait for playback to finish before exiting
    play_obj.wait_done()
    

class CianParser():
    
    def __init__(self, driver):
        self.driver = driver
        
    def get_until_captcha(self, url):
        self.driver.get(url)
        if 'captcha' in self.driver.title.lower():
            play_signal()
            # may need to refresh the page
            time.sleep(TIME_TO_SOLVE) 
#            ui.WebDriverWait(self.driver, timeout=60, poll_frequency=1).until('captcha' not in self.driver.title.lower())
#            wait = ui.WebDriverWait(self.driver, 60)
#            results = wait.until(lambda self.driver: )
        
    def get_number_of_pages(self):
        '''returns the number of pages to be crawled'''
        found_ads = self.driver.find_element_by_xpath('//*[@id="frontend-serp"]/div/div[4]/div[1]/div[1]/h3').text
        ads_number = int(''.join(re.findall(r"\d+", found_ads)))
        return min(MAX_NUMBER_PAGES, (ads_number + 1) // ADS_ON_PAGE)
    
    def get_hrefs_from_page(self):
        '''returns all links on a page that lead to detail pages'''
        elems = self.driver.find_elements_by_xpath('//*[@id="frontend-serp"]/div/div[5]/article/div[1]/div[2]/div[1]/div/a')
        return [e.get_attribute('href') for e in elems]
        
    def get_flat_data(self):
        '''get all information from detail page'''
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        flat_data = {}
        
        info_tag_class = [('price', 'span', "a10a3f92e9--price_value--1iPpd"),
                          ('recommended_price', 'div', '"a10a3f92e9--price--c1gyM"'),
                          ('rooms', 'h1', "a10a3f92e9--title--2Widg"),
                          ('metro', 'a', "a10a3f92e9--underground_link--AzxRC"),
                          ('metro_time', 'span', "a10a3f92e9--underground_time--1fKft"),
                          ('description', 'p', "a10a3f92e9--description-text--3Sal4")
                ]
        
        for i in info_tag_class:
            try:
                flat_data[i[0]] = soup.find(i[1], class_ = i[2]).text
            except:
                pass
        
        try:
            flat_data['address'] = soup.find('div', class_="a10a3f92e9--geo--18qoo").find('span').get('content')
        except:
            pass
        
        try:
            general_info = soup.find('div', class_ = "a10a3f92e9--description--3uuO6").find_all('div', class_="a10a3f92e9--info--3XiXi")
            general_info = [[j.text for j in i] for i in general_info]
            general_info = {item[1]: item[0] for item in general_info}
            flat_data.update(general_info)
        except:
            pass
        
        try:
            for i in soup.find('div', class_ = "a10a3f92e9--section_divider--1zGrv").find_all('li'):
                if len(i.find_all('span')) == 2:
                    flat_data[i.find_all('span')[0].text] = i.find_all('span')[1].text
                if len(i.find_all('span')) == 0:
                    flat_data[i.text] = 1
        except:
            pass
        
        try:
            for i in soup.find('div', class_ = "a10a3f92e9--column--2oGBs"):
                flat_data[i.find_all('div')[0].text] = i.find_all('div')[1].text 
        except:
            pass
        
        try:
            coords = re.findall(r'\{\"l..\":\d*.\d*,\"l..\"\:\d*.\d*\}', soup.text)
            flat_data.update(ast.literal_eval(coords[0]))
        except:
            pass
        
        return flat_data
            
def main():
    
    data = []
    driver = webdriver.Chrome()
    parser = CianParser(driver)
    
    # do not load pictures to speed up?
#    chromeOptions = webdriver.ChromeOptions()
#    prefs = {'profile.managed_default_content_settings.images': 2}
#    chromeOptions.add_experimental_option('prefs', prefs)
#    driver = webdriver.Chrome(chrome_options = chromeOptions)
        
    for i, url in enumerate(districs_url):
        parser.get_until_captcha(url)
        
        for page in tqdm(range(1, parser.get_number_of_pages()), desc = f'Processing URL {i}', position=0, leave=True):
            parser.get_until_captcha(url.replace('&p=2', '&p=' + str(page)))
            for href in parser.get_hrefs_from_page():
                parser.get_until_captcha(href)
                flat_data = parser.get_flat_data()
                flat_data['URL'] = href
                data.append(flat_data)
                # saving
                pd.DataFrame(data).to_csv(PATH_DATA, index = False)                
                # waiting
                time.sleep(uniform(3, 6))
                
            tqdm._instances.clear()
            
    driver.close()
    
if __name__ == '__main__':
    main()
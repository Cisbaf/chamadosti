import tempfile, os, re, base64, json
from typing import List
from selenium.webdriver.common.by import By
from .driver import ChromeDriverController
from dataclasses import dataclass, asdict

@dataclass
class Archive:
    name: str
    bts: bytes

@dataclass
class DatasRegister:
    unity: str
    reason: str
    desc: str
    contact: str

class GLPIFunctions:

    def __init__(self, chrome: ChromeDriverController) -> None:
        self.chrome = chrome
        self.xpath_login = '//*[@id="login_name"]'
        self.xpath_pass = '/html/body/div[1]/div/div/div[2]/div/form/div/div[1]/div[3]/input'
        self.name_title_chamado = 'name'
        self.css_iframe = 'tox-edit-area__iframe'
        self.name_input = '_uploader_filename[]'
        self.xpath_btn = '//*[@id="itil-form"]/div/div[4]/button'

    def login(self, user: str = 'Portal Chamado', passw: str = 'Cisbaf2023'):
        try:
            self.chrome.driver.get("http://192.168.1.235/index.php?noAUTO=1")
            self.chrome.set_value(self.xpath_login, By.XPATH, user)
            self.chrome.set_value(self.xpath_pass, By.XPATH, passw, True)
            if self.chrome.driver.title != "Home - GLPI": # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! warning
                raise Exception("Usuário ou senha invalida")
        except Exception as e:
            raise Exception("ERROR LOGIN - " + str(e))
        
    def open_request(self, protocolo: str, datas: DatasRegister, archives: List[Archive] = None):
        try:
            self.chrome.driver.get("http://192.168.1.235/front/ticket.form.php")
            self.chrome.set_value(self.name_title_chamado, By.NAME, f'{datas.reason} - {protocolo}')
            iframe = self.chrome.get_element(self.css_iframe, By.CLASS_NAME)
            self.chrome.driver.switch_to.frame(iframe)
            paragrafo_element = self.chrome.get_element("p", By.TAG_NAME)
            paragrafo_element.send_keys(datas.desc)
            self.chrome.driver.switch_to.default_content()
            
            if archives and len(archives) > 0:
                for archive in archives:
                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, archive.name)
                    with open(temp_file_path, 'wb') as temp_file:
                        temp_file.write(archive.bts)
                    try:
                        input = self.chrome.get_element(self.name_input, By.NAME)
                        input.send_keys(temp_file_path)
                        self.chrome.progress_bar('uploadbar', By.CLASS_NAME)
                    except:
                        pass
                    os.remove(temp_file_path)
        
            button = self.chrome.get_element(self.xpath_btn, By.XPATH)
            self.chrome.driver.execute_script("arguments[0].click();", button)
           

        except Exception as e:
            self.chrome.driver.close()

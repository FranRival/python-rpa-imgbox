from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_experimental_option("detach", True)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

service = Service(ChromeDriverManager().install(), log_path="chromedriver_debug.log")

driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(30)

print("Driver iniciado. Intentando cargar google.com ...")
driver.get("https://www.google.com")
print("GET enviado. Esperando 5s...")
time.sleep(5)
print("Título de la página:", driver.title)
# no driver.quit() para que la ventana se quede abierta

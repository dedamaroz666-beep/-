import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

soup = BeautifulSoup(open('static/index.html', encoding='utf-8'), 'html.parser')
sec = soup.find('section', class_='charts-section')
for el in sec.find_all(True):
    print(f'<{el.name} id="{el.get("id")}" class="{el.get("class")}" style="{el.get("style")}">{el.string if el.string else ""}')

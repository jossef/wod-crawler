#!/usr/bin/env python3
import hashlib
import json
import requests
from bs4 import BeautifulSoup
import os

MAX_PAGE = 300
BASE_URL = "https://wods.crossfitpanda.com"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def get_latest_user_agent(operating_system='windows', browser='chrome'):
    url = f'https://jnrbsn.github.io/user-agents/user-agents.json'
    r = requests.get(url)
    r.raise_for_status()
    user_agents = r.json()

    for user_agent in user_agents:
        if operating_system.lower() in user_agent.lower() and browser.lower() in user_agent.lower():
            return user_agent

    return None


class WODCrawler:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        user_agent = get_latest_user_agent()
        if not user_agent:
            raise ValueError("No suitable user agent found.")

        self.session.headers.update({
            'User-Agent': user_agent
        })

    def _get_page_workouts(self, page):
        print(f"Crawling page {page}")
        page_url = f"{self.base_url}/page/{page}/"

        response = self.session.get(page_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        articles = soup.find_all('article')
        for article in articles:
            wod_url = article.find('a', href=True).attrs['href']
            wod_url = self.base_url + wod_url
            wod_timestamp = article.find(class_='gh-card-date').attrs['datetime']

            wod_response = self.session.get(wod_url, timeout=30)
            wod_response.raise_for_status()

            wod_soup = BeautifulSoup(wod_response.content, 'html.parser')

            wod_image_url = ''
            wod_image = wod_soup.find(class_='gh-article-image')
            if wod_image:
                wod_image_url = wod_image.find('img').attrs['src']
                wod_image_url = self.base_url + wod_image_url

            wod_description = wod_soup.find(class_='is-body')

            # Add extra newlines between paragraphs
            for p in wod_description.find_all('p'):
                p.append('\n')

            wod_description = wod_description.text.strip()
            yield ({
                'date': wod_timestamp,
                'content': wod_description,
                'image': wod_image_url,
                'url': wod_url
            })

    def sync_workouts(self, full_sync=False):
        print("Starting WOD crawler...")

        workouts_dir = os.path.join(SCRIPT_DIR, "workouts")
        os.makedirs(workouts_dir, exist_ok=True)

        for page in range(1, MAX_PAGE):
            for workout in self._get_page_workouts(page):
                workout_id = hashlib.sha1(workout['url'].encode('utf-8')).hexdigest()[:8]
                file_name = f"{workout['date']}_{workout_id}.json"
                file_path = os.path.join(workouts_dir, file_name)
                if not full_sync and os.path.exists(file_path):
                    print(f"WOD already exist. sync up to this point")
                    return

                print(f'saving WOD: {workout["url"]}')
                with open(file_path, 'w+', encoding='utf-8') as f:
                    json.dump(workout, f, ensure_ascii=False, indent=4)


def main():
    crawler = WODCrawler()
    crawler.sync_workouts()


if __name__ == "__main__":
    main()

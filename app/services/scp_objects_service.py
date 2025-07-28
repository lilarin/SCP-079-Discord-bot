import asyncio
import re
from typing import List, Dict, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.config import config, logger
from app.models import SCPObject


class ScpObjectsService:
    def __init__(self):
        self.urls = config.scrape_urls
        self.wiki_url = config.wiki_url

    @staticmethod
    async def _fetch_html(session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url, timeout=15) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _parse_scp_data(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.find('div', class_="content-panel standalone series")

        if not content_div:
            return []

        found_items = []
        for a_tag in content_div.find_all('a'):
            try:
                href = a_tag.get('href')
                if not href or not href.startswith('/scp-'):
                    continue

                img_tag = a_tag.find_previous_sibling('img')
                if not img_tag:
                    continue

                number_match = re.search(r'\d+', href)
                if not number_match:
                    continue

                scp_number = int(number_match.group(0))
                object_class = img_tag['src'].split('/')[-1].split('.')[0]

                item = {
                    "title": a_tag.get_text(),
                    "range": (scp_number // 1000) + 1,
                    "object_class": object_class if object_class != "na" else None,
                    "link": f"{self.wiki_url}{href}"
                }

                if object_class in ["keter", "exotic", "meta", "safe", "thaumiel", "euclid", "na"]:
                    found_items.append(item)
            except (AttributeError, TypeError, KeyError):
                continue

        return found_items

    async def collect_scp_objects(self) -> List[Dict]:
        all_scp_data = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_html(session, url) for url in self.urls]
            html_pages = await asyncio.gather(*tasks)

            for html in html_pages:
                if html:
                    all_scp_data.extend(self._parse_scp_data(html))

        return all_scp_data

    async def update_scp_objects(self) -> None:
        scp_data = await self.collect_scp_objects()

        existing_links = await SCPObject.all().values_list("link", flat=True)

        new_objects_to_create = []
        for item_data in scp_data:
            if item_data["link"] not in existing_links:
                new_objects_to_create.append(SCPObject(**item_data))

        if new_objects_to_create:
            await SCPObject.bulk_create(new_objects_to_create)
            logger.info(f"Created {len(new_objects_to_create)} SCP objects.")
        else:
            logger.info(f"All SCP objects are up-to-date.")


scp_objects_service = ScpObjectsService()

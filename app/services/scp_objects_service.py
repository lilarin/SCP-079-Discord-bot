import asyncio
import random
import re
from typing import List, Dict, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup, NavigableString

from app.config import config, logger
from app.core.models import SCPObject, User, ViewedScpObject


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
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="page-content")

        if not content_div:
            return []

        found_items = []

        for a_tag in content_div.find_all("a", href=re.compile("/scp-")):
            try:
                href = a_tag["href"]

                img_tag = a_tag.find_previous_sibling("img")
                if not img_tag:
                    continue

                next_node = a_tag.next_sibling
                if not isinstance(next_node, NavigableString) or not str(next_node).strip():
                    continue

                title = str(next_node).lstrip(" -").strip()

                number_match = re.search(r"\d+", href)
                if not number_match:
                    continue

                scp_number = int(number_match.group(0))
                object_class = img_tag["src"].split("/")[-1].split(".")[0]

                item = {
                    "number": a_tag.get_text(),
                    "title": title,
                    "range": (scp_number // 1000) + 1,
                    "object_class": object_class if object_class != "na" else None,
                    "link": f"{self.wiki_url}{href}"
                }

                found_items.append(item)

            except (AttributeError, TypeError, KeyError, IndexError):
                continue

        return found_items

    async def _collect_scp_objects(self) -> List[Dict]:
        all_scp_data = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_html(session, url) for url in self.urls]
            html_pages = await asyncio.gather(*tasks)

            for html in html_pages:
                if html:
                    all_scp_data.extend(self._parse_scp_data(html))

        return all_scp_data

    async def update_scp_objects(self) -> None:
        scp_data = await self._collect_scp_objects()

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

    @staticmethod
    async def get_random_scp_object(
            object_class: Optional[str] = None,
            object_range: Optional[int] = None,
            skip_viewed: bool = False,
            member_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[SCPObject]]:
        filters = {}
        if object_range is not None:
            filters["range"] = object_range
        if object_class is not None:
            filters["object_class"] = object_class

        db_user, _ = await User.get_or_create(user_id=member_id)
        query = SCPObject.filter(**filters)

        if skip_viewed:
            viewed_scp_ids = await db_user.viewed_objects.all().values_list("scp_object_id", flat=True)  # type: ignore
            query = query.exclude(id__in=viewed_scp_ids)

        count = await query.count()
        if count == 0:
            return True, None

        random_offset = random.randint(0, count - 1)
        random_scp_object = await query.offset(random_offset).first()

        if random_scp_object:
            if db_user:
                await ViewedScpObject.get_or_create(user=db_user, scp_object=random_scp_object)

            return False, random_scp_object

        return True, None


scp_objects_service = ScpObjectsService()

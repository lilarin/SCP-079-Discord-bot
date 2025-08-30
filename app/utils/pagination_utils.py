import math
from typing import Tuple


class PaginationUtils:
    @staticmethod
    async def get_last_page_offset(total_count: int, limit: int) -> Tuple[int, int]:
        if total_count == 0:
            return 0, 1
        total_pages = math.ceil(total_count / limit)
        offset = max(0, (total_pages - 1) * limit)
        return offset, total_pages


pagination_utils = PaginationUtils()

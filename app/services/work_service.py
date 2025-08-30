import random
from typing import Tuple

from app.config import config
from app.core.models import User
from app.services.economy_management_service import economy_management_service


class WorkService:
    def __init__(self):
        self.work_prompts = config.work_prompts

    async def _get_user_work_key(self, db_user: User) -> str:
        await db_user.fetch_related("equipped_card")
        if db_user.equipped_card and db_user.equipped_card.item_id in self.work_prompts:
            return db_user.equipped_card.item_id

        return list(self.work_prompts.keys())[-1]

    async def perform_legal_work(self, user: User) -> Tuple[str, int]:
        db_user, _ = await User.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        prompt = random.choice(self.work_prompts[work_key].legal)

        reward = random.randint(*config.legal_work_reward_range)

        await economy_management_service.update_user_balance(user, reward, "Виконнаня легальної роботи")

        return prompt, reward

    async def perform_non_legal_work(self, user: User) -> Tuple[str, int, bool]:
        db_user, _ = await User.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        non_legal_prompts = self.work_prompts[work_key].non_legal

        is_success = random.random() < config.non_legal_work_success_chance

        if is_success:
            prompt = random.choice(non_legal_prompts.success)
            amount = random.randint(*config.non_legal_work_reward_range)
            await economy_management_service.update_user_balance(user, amount, "Вдале виконання ризикованої роботи")
        else:
            prompt = random.choice(non_legal_prompts.failure)
            amount = random.randint(*config.non_legal_work_penalty_range)
            await economy_management_service.update_user_balance(user, -amount, "Невдале виконання ризикованої роботи")

        return prompt, amount, is_success


work_service = WorkService()

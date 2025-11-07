import asyncio
import random

from disnake import User, Embed

from app.core.models import User as UserModel
from app.core.variables import variables
from app.embeds import economy_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_management_service


class WorkService:
    def __init__(self):
        self.work_prompts = variables.work_prompts

    async def _get_user_work_key(self, db_user: UserModel) -> str:
        await db_user.fetch_related("equipped_card")
        if db_user.equipped_card and db_user.equipped_card.item_id in self.work_prompts:
            return db_user.equipped_card.item_id
        return list(self.work_prompts.keys())[-1]

    async def perform_legal_work(self, user: User) -> Embed:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        prompt = random.choice(self.work_prompts[work_key].legal)
        reward = random.randint(*variables.legal_work_reward_range)

        await economy_management_service.update_user_balance(user, reward, t("economy.reasons.legal_work"))
        asyncio.create_task(
            achievement_handler_service.handle_work_achievements(user, is_risky=False, is_success=True)
        )
        return await economy_embeds.format_legal_work_embed(prompt, reward)

    async def perform_non_legal_work(self, user: User) -> Embed:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        non_legal_prompts = self.work_prompts[work_key].non_legal
        is_success = random.random() < variables.non_legal_work_success_chance

        if is_success:
            prompt = random.choice(non_legal_prompts.success)
            amount = random.randint(*variables.non_legal_work_reward_range)
            await economy_management_service.update_user_balance(
                user, amount, t("economy.reasons.risky_work_success")
            )
            asyncio.create_task(
                achievement_handler_service.handle_work_achievements(user, is_risky=True, is_success=True)
            )
        else:
            prompt = random.choice(non_legal_prompts.failure)
            amount = random.randint(*variables.non_legal_work_penalty_range)
            await economy_management_service.update_user_balance(
                user, -amount, t("economy.reasons.risky_work_failure")
            )
            asyncio.create_task(
                achievement_handler_service.handle_work_achievements(user, is_risky=True, is_success=False)
            )

        return await economy_embeds.format_non_legal_work_embed(prompt, amount, is_success)


work_service = WorkService()

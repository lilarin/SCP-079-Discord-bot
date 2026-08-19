import asyncio
import random

from disnake import User, Embed

from app.core.models import User as UserModel, UserItem
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

    @staticmethod
    async def _get_work_card(db_user: UserModel):
        user_items = await UserItem.filter(user=db_user).select_related("item")
        card_configs = [
            variables.cards[user_item.item.item_id]
            for user_item in user_items
            if user_item.item.item_id in variables.cards
        ]
        return max(card_configs, key=lambda card: card.work_progression_rank, default=None)

    async def perform_legal_work(self, user: User) -> Embed:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        work_card = await self._get_work_card(db_user)
        prompt = random.choice(self.work_prompts[work_key].legal)
        multiplier = work_card.work_reward_multiplier if work_card and work_card.work_reward_multiplier else 1.0
        reward = round(random.randint(*variables.legal_work_reward_range) * multiplier)

        await economy_management_service.update_user_balance(user, reward, t("economy.reasons.legal_work"))
        asyncio.create_task(
            achievement_handler_service.handle_work_achievements(user, is_risky=False, is_success=True)
        )
        return await economy_embeds.format_legal_work_embed(prompt, reward)

    async def perform_non_legal_work(self, user: User) -> Embed:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        work_key = await self._get_user_work_key(db_user)
        work_card = await self._get_work_card(db_user)
        non_legal_prompts = self.work_prompts[work_key].non_legal
        is_success = random.random() < variables.non_legal_work_success_chance

        if is_success:
            prompt = random.choice(non_legal_prompts.success)
            multiplier = work_card.work_reward_multiplier if work_card and work_card.work_reward_multiplier else 1.0
            amount = round(random.randint(*variables.non_legal_work_reward_range) * multiplier)
            await economy_management_service.update_user_balance(
                user, amount, t("economy.reasons.risky_work_success")
            )
            asyncio.create_task(
                achievement_handler_service.handle_work_achievements(user, is_risky=True, is_success=True)
            )
        else:
            prompt = random.choice(non_legal_prompts.failure)
            multiplier = work_card.risky_work_penalty_multiplier if work_card else 1.0
            amount = round(random.randint(*variables.non_legal_work_penalty_range) * multiplier)
            await economy_management_service.update_user_balance(
                user, -amount, t("economy.reasons.risky_work_failure")
            )
            asyncio.create_task(
                achievement_handler_service.handle_work_achievements(user, is_risky=True, is_success=False)
            )

        return await economy_embeds.format_non_legal_work_embed(prompt, amount, is_success)


work_service = WorkService()

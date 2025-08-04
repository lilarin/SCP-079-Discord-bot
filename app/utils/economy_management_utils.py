from disnake import Embed


class EconomyManagementUtils:
    @staticmethod
    async def format_balance_embed(balance: int, reputation: int, position: int) -> Embed:
        embed = Embed(
            title="Баланс репутації користувача",
            description="",
            color=0xffffff
        )

        embed.description += f"Поточний баланс – {balance} 💠 \n\n-# Загальна кількість заробленої репутації – {reputation} 🔰"

        if position:
            embed.description += f"\n-# **#{position} у рейтингу серед співробітників**"

        return embed


economy_management_utils = EconomyManagementUtils()

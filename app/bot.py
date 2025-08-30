import asyncio

import asyncpg
import disnake
from disnake.ext import commands

from app.config import config, logger
from app.core.decorators import target_is_user, remove_bet_from_balance
from app.core.models import User
from app.modals.dossier_modal import DossierModal
from app.services import (
    article_service,
    economy_management_service,
    candy_game_service,
    coin_flip_service,
    coguard_service,
    crystallization_service,
    hole_game_service,
    staring_game_service,
    inventory_service,
    keycard_service,
    leaderboard_service,
    scp_objects_service,
    shop_service,
    work_service,
    achievement_service,
    economy_logging_service,
    achievement_handler_service
)
from app.utils.pagination import pagination_utils
from app.utils.response_utils import response_utils
from app.utils.time_utils import time_utils
from app.utils.ui_utils import ui_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
    try:
        await scp_objects_service.update_scp_objects()
        await shop_service.sync_card_items()
        await achievement_service.sync_achievements()
        await economy_logging_service.init_logging(bot)
    except asyncpg.exceptions.InternalServerError as exception:
        logger.error(exception)
    logger.info(f"Виконано вхід як {bot.user}")
    await asyncio.sleep(1)
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.watching,
            name="на особові справи"
        )
    )


@bot.event
async def on_slash_command(interaction):
    user = interaction.user
    command = interaction.data.name
    logger.info(f"Користувач {user} використав команду /{command}")


@bot.event
async def on_slash_command_error(interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await response_utils.send_ephemeral_response(interaction, "Ця команда недоступна для вас")
        return
    elif isinstance(error, commands.NoPrivateMessage):
        await response_utils.send_ephemeral_response(interaction, "Команди бота можна використовувати лише на сервері")
        return
    elif isinstance(error, disnake.ext.commands.errors.CommandOnCooldown):
        timestamp = await time_utils.get_current()
        timestamp = round(timestamp.timestamp() + error.retry_after)
        await response_utils.send_ephemeral_response(
            interaction,
            f"Ви поки не можете використати цю команду, спробуйте знову <t:{timestamp}:R>"
        )

    logger.error(error)


@bot.event
async def on_member_join(member):
    try:
        templates = list(config.cards.values())
        template = templates[-1]

        card = await keycard_service.generate_image(member, template)
        embed = await ui_utils.format_new_user_embed(member.mention, card, template.embed_color)

        await member.guild.system_channel.send(embed=embed)

        await User.get_or_create(user_id=member.id)

    except asyncpg.exceptions.InternalServerError as error:
        logger.error(error)
    except Exception as exception:
        logger.error(exception)


@bot.slash_command(name="картка", description="Переглянути картку співробітника фонду")
@commands.guild_only()
@target_is_user
async def view_card(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None, name="користувач"),
):
    await response_utils.wait_for_response(interaction)
    member = user or interaction.user

    try:
        profile_data = await keycard_service.get_user_profile_data(member)

        embed = await ui_utils.format_user_embed(
            card=profile_data.card_image,
            color=profile_data.card_template.embed_color,
            dossier=profile_data.dossier,
            role=profile_data.top_role,
            achievements_count=profile_data.achievements_count
        )

        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=1, per=config.article_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="випадкова-стаття", description="Отримати посилання на випадкову статтю за фільтрами")
@commands.guild_only()
async def get_random_article(
        interaction: disnake.ApplicationCommandInteraction,
        object_class=commands.Param(
            choices=list(config.scp_classes.keys()),
            description="Клас об'єкту (необов'язково)",
            default=None, name="клас"
        ),
        object_range=commands.Param(
            choices=list(config.scp_ranges.keys()),
            description="Діапазон номеру об'єкту (необов'язково)",
            default=None, name="діапазон"
        ),
        skip_viewed: bool = commands.Param(
            choices=[True, False],
            description="Виключити вже переглянуті? (необов'язково, увімкнено)",
            default=True, name="пропустити-переглянуті"
        )
):
    await response_utils.wait_for_response(interaction)

    try:
        found_all, random_article = await scp_objects_service.get_random_scp_object(
            object_class=config.scp_classes[object_class] if object_class else None,
            object_range=config.scp_ranges[object_range] if object_range else None,
            skip_viewed=skip_viewed,
            member_id=interaction.user.id,
        )

        if found_all:
            await response_utils.send_response(
                interaction, message="Ви переглянули всі статті за цими фільтрами", delete_after=10
            )
        elif random_article:
            image = await article_service.create_article_image(random_article)

            embed, components = await ui_utils.format_article_embed(random_article, image)
            await response_utils.send_response(interaction, embed=embed, components=components)
        else:
            await response_utils.send_response(
                interaction, message="Статті за цими фільтрами не знайдено", delete_after=10
            )

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="досьє", description="Заповнити своє досьє")
@commands.guild_only()
async def view_card(interaction: disnake.ApplicationCommandInteraction):
    try:
        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        await interaction.response.send_modal(
            modal=DossierModal(user=interaction.user, db_user=db_user)
        )
        await achievement_handler_service.handle_dossier_achievements(interaction.user)
    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="топ", description="Показати топ користувачів за певним критерієм")
@commands.guild_only()
async def top_articles(
        interaction: disnake.ApplicationCommandInteraction,
        criteria=commands.Param(
            choices=list(config.leaderboard_options.keys()),
            description="Критерій для перегляду списку лідерів",
            name="критерій"
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        chosen_criteria = config.leaderboard_options[criteria]
        embed, components = await leaderboard_service.init_leaderboard_message(chosen_criteria)
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="баланс", description="Переглянути баланс користувача")
@commands.guild_only()
@target_is_user
async def view_balance(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None, name="користувач"),
):
    await response_utils.wait_for_response(interaction)
    target_user = user or interaction.user

    try:
        embed = await economy_management_service.create_user_balance_message(target_user)
        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="переказ", description="Надіслати власні 💠 іншому користувачу")
@commands.guild_only()
async def transfer_balance(
        interaction: disnake.ApplicationCommandInteraction,
        recipient: disnake.User = commands.Param(description="Оберіть отримувача", name="отримувач"),
        amount: int = commands.Param(description="Сума для переводу", name="сума", ge=100),
):
    await response_utils.wait_for_response(interaction)

    try:
        success, message = await economy_management_service.transfer_balance(
            interaction.user.id, recipient.id, amount
        )
        if success:
            await response_utils.send_response(interaction, message)
        else:
            await response_utils.send_response(interaction, message, delete_after=10)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="магазин", description="Переглянути товари у магазині")
@commands.guild_only()
async def shop(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)
    try:
        embed, components = await shop_service.init_shop_message()
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="купити", description="Купити товар з магазину за його ID")
@commands.guild_only()
async def buy_item(
        interaction: disnake.ApplicationCommandInteraction,
        item_id: str = commands.Param(description="ID товару", name="предмет"),
):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        await User.get_or_create(user_id=interaction.user.id)

        message = await shop_service.buy_item(
            user_id=interaction.user.id,
            item_id=item_id
        )

        await response_utils.edit_ephemeral_response(interaction, message=message)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="інвентар", description="Переглянути свій інвентар")
@commands.guild_only()
async def inventory(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        await inventory_service.check_for_default_card(user=db_user)

        embed, components = await inventory_service.init_inventory_message(user=interaction.user)
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="екіпірувати", description="Екіпірувати картку доступу з інвентаря")
@commands.guild_only()
async def equip_item(
        interaction: disnake.ApplicationCommandInteraction,
        item_id: str = commands.Param(description="ID картки, яку ви хочете екіпірувати", name="картка"),
):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        await User.get_or_create(user_id=interaction.user.id)

        message = await inventory_service.equip_item(
            user_id=interaction.user.id,
            item_id=item_id
        )

        await response_utils.edit_ephemeral_response(interaction, message=message)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=1, per=config.work_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="робота", description="Виконати безпечне завдання для фонду")
@commands.guild_only()
async def legal_work(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        prompt, reward = await work_service.perform_legal_work(user=interaction.user)

        embed = await ui_utils.format_legal_work_embed(
            prompt=prompt,
            reward=reward
        )

        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=1, per=config.work_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="ризикована-робота", description="Взятися за ризиковану справу")
@commands.guild_only()
async def non_legal_work(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        prompt, amount, is_success = await work_service.perform_non_legal_work(user=interaction.user)

        embed = await ui_utils.format_non_legal_work_embed(
            prompt=prompt,
            amount=amount,
            is_success=is_success
        )

        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="скинути-репутацію", description="Скинути загальну репутацію всіх співробітників")
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def reset_reputation(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        await economy_management_service.reset_users_reputation()
        await response_utils.send_response(
            interaction, "Загальна репутація всіх гравців було скинуто до початкового стану"
        )

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name="змінити-баланс-користувача", description="Збільшити, або зменшити баланс на певну кількість репутації")
@commands.guild_only()
@commands.has_permissions(administrator=True)
@target_is_user
async def edit_player_balance_reputation(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", name="користувач"),
        amount: int = commands.Param(description="Кількість репутації для збільшення, або зменшення", name="баланс"),
):
    await response_utils.wait_for_response(interaction)

    try:
        await economy_management_service.update_user_balance(
            user, amount, (
                f"Зміна балансу користувачу\n"
                f"-# Викликано користувачем {interaction.user.mention}"
            )
        )

        await response_utils.send_response(
            interaction, f"Баланс гравця {user.mention} було змінено"
        )

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="кристалізація", description="Почати процес кристалізації")
@commands.guild_only()
@remove_bet_from_balance
async def game_crystallize(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
):
    try:
        await crystallization_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="монетка", description="Підкинути монетку та випробувати вдачу")
@commands.guild_only()
@remove_bet_from_balance
async def game_coin_flip(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
):
    try:
        await coin_flip_service.play_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="цукерки", description="Випробуйте свою вдачу з SCP-330")
@commands.guild_only()
@remove_bet_from_balance
async def game_candy(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
):
    try:
        await candy_game_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="когнітивна-стійкість", description="Пройти тест на когнітивну стійкість")
@commands.guild_only()
@remove_bet_from_balance
async def game_coguard(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
):
    try:
        await coguard_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@bot.slash_command(name="піжмурки", description="Зіграти в піжмурки проти інших гравців з SCP-173")
@commands.guild_only()
@remove_bet_from_balance
async def game_scp173(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
        mode: str = commands.Param(
            description="Режим гри для лоббі",
            choices={
                "Звичайний": "normal",
                "До останнього": "last_man_standing"
            },
            name="режим-гри"
        )
):
    try:
        await staring_game_service.start_lobby(interaction, bet, mode)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name="діра", description="Зробіть ставку в аномальній рулетці")
@commands.guild_only()
@remove_bet_from_balance
async def game_hole(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000, name="ставка"),
        group_bet: str = commands.Param(
            description="Виберіть групову ставку (не можна використовувати разом зі ставкою на предмет)",
            choices=list(config.hole_group_bet_options.keys()),
            default=None,
            name="група"
        ),
        item_bet: str = commands.Param(
            description="Виберіть конкретний предмет (не можна використовувати з груповою ставкою)",
            autocomplete=hole_game_service.item_autocomplete,
            default=None,
            name="предмет"
        )
):
    if (group_bet and item_bet) or (not group_bet and not item_bet):
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Неправильна ставка під час гри {interaction.data.name}"
        )
        await response_utils.send_response(
            interaction, "Необхідно обрати **один** тип ставки", delete_after=10
        )
        return

    if item_bet and item_bet not in config.hole_items.values():
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Неправильна ставка під час гри {interaction.data.name}"
        )
        await response_utils.send_response(
            interaction, f"Опцію '{item_bet}' не знайдено, оберіть зі списку", delete_after=10
        )
        return

    final_choice = group_bet or item_bet

    try:
        if hole_game_service.is_game_active(interaction.channel.id):
            await hole_game_service.join_game(interaction, bet, final_choice)
        else:
            await hole_game_service.create_game(interaction, bet, final_choice)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        await economy_management_service.update_user_balance(
            interaction.user, bet, f"Помилка під час гри `{interaction.data.name}`"
        )


@bot.slash_command(name="досягнення-користувача", description="Показати отримані досягнення")
@commands.guild_only()
@target_is_user
async def achievements(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None, name="користувач"),
):
    await response_utils.wait_for_response(interaction)
    target_user = user or interaction.user

    try:
        embed, components = await achievement_service.init_achievements_message(target_user)
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as e:
        logger.error(f"Помилка при отриманні досягнень: {e}")
        await response_utils.send_response(interaction, "Не вдалося завантажити досягнення", delete_after=10)


@bot.slash_command(name="список-досягнень", description="Показати список та статистику отримання досягнень на сервері")
@commands.guild_only()
async def achievement_stats(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        embed, components = await achievement_service.init_stats_message()
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)
    except Exception as e:
        logger.error(f"Помилка при отриманні статистики досягнень: {e}")
        await response_utils.edit_ephemeral_response(interaction, "Не вдалося завантажити список досягнень ")


@bot.event
async def on_button_click(interaction: disnake.MessageInteraction) -> None:
    await interaction.response.defer()

    interaction_component_id = interaction.component.custom_id

    if interaction_component_id == "game_scp173_join":
        await staring_game_service.handle_join(interaction)
        return

    if interaction.user != interaction.message.interaction_metadata.user:
        await response_utils.send_ephemeral_response(
            interaction,
            (
                "Ви не можете керувати цим повідомленням "
                "\n-# Тільки користувач, що викликав команду може з ним взаємодіяти"
            )
        )
        return

    try:
        if "game" in interaction_component_id:
            if interaction_component_id == "game_crystallize_continue":
                await crystallization_service.continue_game(interaction)
            elif interaction_component_id == "game_crystallize_stop":
                await crystallization_service.cash_out(interaction)
            elif interaction_component_id == "game_candy_take":
                await candy_game_service.take_candy(interaction)
            elif interaction_component_id == "game_candy_leave":
                await candy_game_service.leave_game(interaction)
            elif interaction_component_id == "game_coguard_higher":
                await coguard_service.play_turn(interaction, 'higher')
            elif interaction_component_id == "game_coguard_lower":
                await coguard_service.play_turn(interaction, 'lower')
            elif interaction_component_id == "game_coguard_cashout":
                await coguard_service.cash_out(interaction)
            elif interaction_component_id == "game_scp173_start":
                await staring_game_service.handle_start(interaction)
                return
            return

        current_page = int(interaction.message.components[0].children[2].label)

        if "shop" in interaction_component_id:
            if "previous" in interaction_component_id:
                offset = (current_page - 2) * config.shop_items_per_page
                current_page -= 1
            elif "next" in interaction_component_id:
                offset = current_page * config.shop_items_per_page
                current_page += 1
            elif "last" in interaction_component_id:
                total_count = await shop_service.get_total_items_count()
                offset, current_page = await pagination_utils.get_last_page_offset(
                    total_count=total_count, limit=config.shop_items_per_page
                )
            else:
                current_page = 1
                offset = 0

            embed, components = await shop_service.edit_shop_message(current_page, offset)
            await response_utils.edit_response(interaction, embed=embed, components=components)
            return

        if "inventory" in interaction_component_id:
            user = interaction.user

            if "previous" in interaction_component_id:
                offset = (current_page - 2) * config.inventory_items_per_page
                current_page -= 1
            elif "next" in interaction_component_id:
                offset = current_page * config.inventory_items_per_page
                current_page += 1
            elif "last" in interaction_component_id:
                total_count = await inventory_service.get_total_user_items_count(user.id)
                offset, current_page = await pagination_utils.get_last_page_offset(
                    total_count=total_count, limit=config.inventory_items_per_page
                )
            else:
                current_page = 1
                offset = 0

            embed, components = await inventory_service.edit_inventory_message(
                user, current_page, offset
            )

            await interaction.edit_original_message(embed=embed, components=components)
            return

        if "achievements_stats" in interaction_component_id:
            if "previous" in interaction_component_id:
                offset = (current_page - 2) * config.achievements_per_page
                current_page -= 1
            elif "next" in interaction_component_id:
                offset = current_page * config.achievements_per_page
                current_page += 1
            elif "last" in interaction_component_id:
                total_count = await achievement_service.get_total_achievements_count()
                offset, current_page = await pagination_utils.get_last_page_offset(
                    total_count=total_count, limit=config.achievements_per_page
                )
            else:
                current_page = 1
                offset = 0

            embed, components = await achievement_service.edit_stats_message(current_page, offset)
            await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)
            return

        if "achievements" in interaction_component_id:
            target_user_id = interaction.message.components[0].children[2].custom_id
            if target_user_id != str(interaction.message.interaction_metadata.user.id):
                target_user = await bot.get_or_fetch_user(int(target_user_id))
            else:
                target_user = interaction.message.interaction_metadata.user

            if "previous" in interaction_component_id:
                offset = (current_page - 2) * config.achievements_per_page
                current_page -= 1
            elif "next" in interaction_component_id:
                offset = current_page * config.achievements_per_page
                current_page += 1
            elif "last" in interaction_component_id:
                total_count = await achievement_service.get_total_user_achievements_count(target_user.id)
                offset, current_page = await pagination_utils.get_last_page_offset(
                    total_count=total_count, limit=config.achievements_per_page
                )
            else:
                current_page = 1
                offset = 0

            embed, components = await achievement_service.edit_achievements_message(
                target_user, current_page, offset
            )
            await interaction.edit_original_message(embed=embed, components=components)
            return

        for criteria in config.leaderboard_options.values():
            if criteria in interaction_component_id:
                if "previous" in interaction_component_id:
                    offset = (current_page - 2) * config.leaderboard_items_per_page
                    current_page -= 1
                elif "next" in interaction_component_id:
                    offset = current_page * config.leaderboard_items_per_page
                    current_page += 1
                elif "last" in interaction_component_id:
                    total_count = await leaderboard_service.get_total_users_count(criteria)
                    offset, current_page = await pagination_utils.get_last_page_offset(
                        total_count=total_count, limit=config.leaderboard_items_per_page
                    )
                else:
                    current_page = 1
                    offset = 0

                embed, components = await leaderboard_service.edit_leaderboard_message(
                    criteria, current_page, offset
                )

                await response_utils.edit_response(interaction, embed=embed, components=components)
                break

    except Exception as exception:
        logger.error(exception)

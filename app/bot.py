import asyncio

import asyncpg
import disnake
from disnake.ext import commands

from app.config import config, logger
from app.core.decorators import target_is_user, remove_bet_from_balance
from app.modals.dossier_modal import DossierModal
from app.core.models import User
from app.services.articles_service import article_service
from app.services.economy_management_service import economy_management_service
from app.services.game_candy_service import candy_game_service
from app.services.game_coin_service import coin_flip_service
from app.services.game_conguard_service import coguard_service
from app.services.game_crystallization_service import crystallization_service
from app.services.game_hole_service import hole_game_service
from app.services.game_staring_service import staring_game_service
from app.services.inventory_service import inventory_service
from app.services.keycard_service import keycard_service
from app.services.leaderboard_service import leaderboard_service
from app.services.scp_objects_service import scp_objects_service
from app.services.shop_service import shop_service
from app.services.work_service import work_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
    await scp_objects_service.update_scp_objects()
    await shop_service.sync_card_items()
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
    user = interaction.author
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

    logger.error(error)


@bot.event
async def on_member_join(member):
    try:
        templates = list(config.cards.values())
        template = templates[-1]

        embed = await keycard_service.create_new_user_embed(member, template)

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
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None),
):
    await response_utils.wait_for_response(interaction)
    member = user or interaction.user

    try:
        db_user, created = await User.get_or_create(user_id=member.id)
        await db_user.fetch_related("equipped_card")

        template = None
        if db_user.equipped_card:
            equipped_template_id = db_user.equipped_card.item_id
            if equipped_template_id in config.cards:
                template = config.cards[equipped_template_id]

        if not template:
            templates = list(config.cards.values())
            template = templates[-1]

        image = await keycard_service.generate_image(member, template)

        db_user, created = await User.get_or_create(user_id=member.id)

        try:
            top_role = member.top_role if member.top_role != interaction.guild.default_role else None
        except AttributeError:
            top_role = None

        embed = await keycard_service.create_profile_embed(
            card=image,
            color=template.embed_color,
            dossier=db_user.dossier if not created else None,
            role=top_role,
        )

        await response_utils.send_response(interaction, embed=embed)

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання користувача")
        logger.error(exception)
    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час виконання команди")
        logger.error(exception)


@bot.slash_command(name="випадкова-стаття", description="Отримати посилання на випадкову статтю за фільтрами")
@commands.guild_only()
async def get_random_article(
        interaction: disnake.ApplicationCommandInteraction,
        object_class=commands.Param(
            choices=list(config.scp_classes.keys()),
            description="Клас об'єкту (необов'язково)", default=None
        ),
        object_range=commands.Param(
            choices=list(config.scp_ranges.keys()),
            description="Діапазон номеру об'єкту (необов'язково)", default=None
        ),
        skip_viewed: bool = commands.Param(
            choices=[True, False],
            description="Виключити вже переглянуті? (необов'язково, увімкнено)", default=True
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
                interaction, message="Ви переглянули всі статті за цими фільтрами.", delete_after=5
            )
        elif random_article:
            image = await article_service.create_article_image(random_article)

            embed, components = await ui_utils.format_article_embed(random_article, image)
            await response_utils.send_response(interaction, embed=embed, components=components)
        else:
            await response_utils.send_response(
                interaction, message="Статті за цими фільтрами не знайдено.", delete_after=5
            )

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання cтатті")
        logger.error(exception)


@bot.slash_command(name="досьє", description="Заповнити своє досьє")
@commands.guild_only()
async def view_card(interaction: disnake.ApplicationCommandInteraction):

    try:
        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        await interaction.response.send_modal(
            modal=DossierModal(user=interaction.user, db_user=db_user)
        )
    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.wait_for_ephemeral_response(
            interaction, "Виникла помилка під час отримання користувача"
        )
        logger.error(exception)


@bot.slash_command(name="топ", description="Показати топ користувачів за певним критерієм")
@commands.guild_only()
async def top_articles(
        interaction: disnake.ApplicationCommandInteraction,
        criteria=commands.Param(
            choices=list(config.leaderboard_options.keys()),
            description="Критерій для перегляду списку лідерів"
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        chosen_criteria = config.leaderboard_options[criteria]
        embed, components = await leaderboard_service.init_leaderboard_message(chosen_criteria)
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання топу")
        logger.error(exception)


@bot.slash_command(name="баланс", description="Переглянути баланс користувача")
@commands.guild_only()
@target_is_user
async def view_balance(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None),
):
    await response_utils.wait_for_response(interaction)
    member = user or interaction.user

    try:
        embed = await economy_management_service.create_user_balance_message(member.id)
        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання балансу користувача")
        logger.error(exception)


@bot.slash_command(name="магазин", description="Переглянути товари у магазині")
@commands.guild_only()
async def shop(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)
    try:
        embed, components = await shop_service.init_shop_message()
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час відкриття магазину")
        logger.error(exception)


@bot.slash_command(name="купити", description="Купити товар з магазину за його ID")
@commands.guild_only()
async def buy_item(
        interaction: disnake.ApplicationCommandInteraction,
        item_id: str = commands.Param(description="ID товару"),
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
        await response_utils.send_response(
            interaction, "Виникла помилка під час виконання покупки."
        )
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
        await response_utils.edit_ephemeral_response(
            interaction, message="Виникла помилка під час перегляду інвентаря."
        )
        logger.error(exception)


@bot.slash_command(name="екіпірувати", description="Екіпірувати картку доступу з інвентаря")
@commands.guild_only()
async def equip_item(
    interaction: disnake.ApplicationCommandInteraction,
    item_id: str = commands.Param(description="ID картки, яку ви хочете екіпірувати"),
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
        await response_utils.edit_ephemeral_response(
            interaction, message="Виникла помилка під час екіпірування предмету."
        )
        logger.error(exception)


@bot.slash_command(name="робота", description="Виконати безпечне завдання для фонду")
@commands.guild_only()
async def legal_work(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        prompt, reward = await work_service.perform_legal_work(user_id=interaction.user.id)

        embed = await ui_utils.format_legal_work_embed(
            prompt=prompt,
            reward=reward
        )

        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_response(
            interaction, "Виникла помилка під час виконання завдання."
        )
        logger.error(exception)


@bot.slash_command(name="ризикована-робота", description="Взятися за ризиковану справу")
@commands.guild_only()
async def non_legal_work(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        prompt, amount, is_success = await work_service.perform_non_legal_work(user_id=interaction.user.id)

        embed = await ui_utils.format_non_legal_work_embed(
            prompt=prompt,
            amount=amount,
            is_success=is_success
        )

        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_response(
            interaction, "Виникла помилка під час виконання завдання."
        )
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
        await response_utils.send_response(
            interaction, "Виникла помилка під час скидання репутації всіх гравців"
        )
        logger.error(exception)


@bot.slash_command(name="змінити-баланс-користувача", description="Збільшити, або зменшити баланс на певну кількість репутації")
@commands.guild_only()
@commands.has_permissions(administrator=True)
@target_is_user
async def edit_player_balance_reputation(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача"),
        amount: int = commands.Param(description="Кількість репутації"),
):
    await response_utils.wait_for_response(interaction)

    try:
        await economy_management_service.update_user_balance(user.id, amount)
        await response_utils.send_response(
            interaction, f"Баланс гравця {user.mention} було змінено"
        )

    except Exception as exception:
        await response_utils.send_response(
            interaction, "Виникла помилка під час зміни поточної репутації гравцю"
        )
        logger.error(exception)


@bot.slash_command(name="кристалізація", description="Почати процес кристалізації")
@commands.guild_only()
@remove_bet_from_balance
async def game_crystallize(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
):
    try:
        await crystallization_service.start_game(interaction, bet)
    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час гри в кристалізацію"
        )
        logger.error(exception)


@bot.slash_command(name="монетка", description="Підкинути монетку та випробувати вдачу")
@commands.guild_only()
@remove_bet_from_balance
async def game_coin_flip(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
):
    try:
        await coin_flip_service.play_game(interaction, bet)
    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час гри в монетку"
        )
        logger.error(exception)


@bot.slash_command(name="цукерки", description="Випробуйте свою вдачу з SCP-330")
@commands.guild_only()
@remove_bet_from_balance
async def game_candy(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
):
    try:
        await candy_game_service.start_game(interaction, bet)
    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час запуску гри в цукерки"
        )
        logger.error(exception)


@bot.slash_command(name="когнітивна-стійкість", description="Пройти тест на когнітивну стійкість")
@commands.guild_only()
@remove_bet_from_balance
async def game_coguard(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
):
    try:
        await coguard_service.start_game(interaction, bet)
    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час запуску тесту"
        )
        logger.error(exception)


@bot.slash_command(name="піжмурки", description="Зіграти в піжмурки проти інших гравців з SCP-173")
@commands.guild_only()
@remove_bet_from_balance
async def game_scp173(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
    mode: str = commands.Param(
        description="Режим гри",
        choices={
            "Звичайний": "normal",
            "До останнього": "last_man_standing"
        }
    )
):
    try:
        await staring_game_service.start_lobby(interaction, bet, mode)
    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час запуску гри в піжмурки"
        )
        logger.error(exception)


@bot.slash_command(name="діра", description="Зробіть ставку в аномальній рулетці")
@commands.guild_only()
@remove_bet_from_balance
async def game_hole(
    interaction: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(description="Сума вашої ставки", ge=100, le=10000),
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
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, "Необхідно обрати **один** тип ставки", delete_after=5
        )
        return

    if item_bet and item_bet not in config.hole_items.values():
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, f"Опцію '{item_bet}' не знайдено, оберіть зі списку", delete_after=5
        )
        return

    final_choice = group_bet or item_bet

    try:
        if hole_game_service.is_game_active(interaction.channel.id):
            await hole_game_service.join_game(interaction, bet, final_choice)
        else:
            await hole_game_service.create_game(interaction, bet, final_choice)

    except Exception as exception:
        await economy_management_service.update_user_balance(interaction.author.id, bet)
        await response_utils.send_response(
            interaction, message="Виникла помилка під час гри в діру"
        )
        logger.error(exception)


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
                offset, current_page = await shop_service.get_last_page_offset(
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
                offset, current_page = await inventory_service.get_last_page_offset(
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
                    offset, current_page = await leaderboard_service.get_last_page_offset(
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

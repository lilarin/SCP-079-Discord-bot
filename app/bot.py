import asyncio
import random

import asyncpg
import disnake
from disnake.ext import commands

from app.config import config, logger
from app.modals.dossier_modal import DossierModal
from app.models import User
from app.services.articles_service import article_service
from app.services.economy_management_service import economy_management_service
from app.services.keycard_service import keycard_service
from app.services.leaderboard_service import leaderboard_service
from app.services.scp_objects_service import scp_objects_service
from app.utils.articles_utils import article_utils
from app.utils.response_utils import response_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
    await scp_objects_service.update_scp_objects()
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

    logger.error(error)


@bot.event
async def on_member_join(member):
    try:
        template = config.templates[-1]

        embed = await keycard_service.create_new_user_embed(member, template)

        await member.guild.system_channel.send(embed=embed)

        await User.get_or_create(user_id=member.id)

    except asyncpg.exceptions.InternalServerError as error:
        logger.error(error)
    except Exception as exception:
        logger.error(exception)


@bot.slash_command(name="картка", description="Переглянути картку співробітника фонду")
async def view_card(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="Оберіть користувача", default=None),
):
    await response_utils.wait_for_response(interaction)

    member = user or interaction.user
    if member.bot:
        await response_utils.send_response(
            interaction, message="Команду не можна використовувати на ботах.", delete_after=5
        )
        return

    try:
        template = config.templates[random.randint(0, len(config.templates) - 1)]

        image = await keycard_service.generate_image(member, template)

        db_user, created = await User.get_or_create(user_id=member.id)
        top_role = member.top_role

        embed = await keycard_service.create_profile_embed(
            card=image,
            color=template.embed_color,
            dossier=db_user.dossier if not created else None,
            role=top_role if top_role != member.guild.default_role else None,
        )

        await response_utils.send_response(interaction, embed=embed)

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання користувача")
        logger.error(exception)
    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час виконання команди")
        logger.error(exception)


@bot.slash_command(name="випадкова-стаття", description="Отримати посилання на випадкову статтю за фільтрами")
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

            embed, components = article_utils.format_article_embed(random_article, image)
            await response_utils.send_response(interaction, embed=embed, components=components)
        else:
            await response_utils.send_response(
                interaction, message="Статті за цими фільтрами не знайдено.", delete_after=5
            )

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання cтатті")
        logger.error(exception)


@bot.slash_command(name="досьє", description="Заповнити своє досьє")
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
async def view_balance(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="Оберіть користувача", default=None),
):
    await response_utils.wait_for_response(interaction)

    member = user or interaction.user
    if member.bot:
        await response_utils.send_response(
            interaction, message="Команду не можна використовувати на ботах.", delete_after=5
        )
        return

    try:
        embed = await economy_management_service.create_user_balance_message(member.id)
        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання балансу користувача")
        logger.error(exception)


@bot.slash_command(name="скинути-репутацію", description="Скинути загальну репутацію всіх співробітників")
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
@commands.has_permissions(administrator=True)
async def edit_player_balance_reputation(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="Оберіть користувача"),
        amount: int = commands.Param(description="Кількість репутації"),
):
    await response_utils.wait_for_response(interaction)

    if user.bot:
        await response_utils.send_response(
            interaction, message="Команду не можна використовувати на ботах.", delete_after=5
        )
        return

    try:
        await economy_management_service.update_user_balance(user.id, amount)
        await response_utils.send_response(
            interaction, f"Поточна репутація гравця {user.mention} була змінена"
        )

    except Exception as exception:
        await response_utils.send_response(
            interaction, "Виникла помилка під час зміни поточної репутації гравцю"
        )
        logger.error(exception)


@bot.event
async def on_button_click(interaction: disnake.MessageInteraction) -> None:
    await interaction.response.defer()

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
        interaction_component_id = interaction.component.custom_id
        current_page = int(interaction.message.components[0].children[2].label)

        for criteria in config.leaderboard_options.values():
            if criteria in interaction_component_id:
                if "previous" in interaction_component_id:
                    offset = (current_page - 2) * 10
                    current_page -= 1
                elif "next" in interaction_component_id:
                    offset = current_page * 10
                    current_page += 1
                elif "last" in interaction_component_id:
                    total_count = await leaderboard_service.get_total_users_count(criteria)
                    offset, current_page = await leaderboard_service.get_last_page_offset(total_count)
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


# @bot.slash_command(name="пнути", description="???")
# @commands.has_permissions(administrator=True)
# async def spam(
#         interaction: disnake.ApplicationCommandInteraction,
#         user: disnake.User = commands.Param(description="Оберіть користувача"),
#         threads: int = commands.Param(
#             description="Кількість гілок для надсилання повідомлень",
#             default=25, max_value=25
#         ),
#         messages: int = commands.Param(
#             description="Кількість надісланих повідомлень у кожній гілці",
#             default=400, max_value=4000
#         ),
#         delete_existing_threads: bool = commands.Param(
#             description="Видалити існуючі гілки в каналі?",
#             default=False
#         ),
# ):
#     await response_utils.wait_for_ephemeral_response(interaction)
#
#     if interaction.channel.type != disnake.ChannelType.text:
#         await response_utils.send_response(
#             interaction,
#             message=f"Команду можна використовувати лише в **текстових** каналах"
#         )
#         return
#
#     if user.bot:
#         await response_utils.send_response(
#             interaction,
#             message=f"Команду не можна використовувати на ботах"
#         )
#         return
#
#     await response_utils.send_response(
#         interaction,
#         message=f"{user.mention} поплачет"
#     )
#
#     channel = interaction.channel
#     if delete_existing_threads:
#         for channel_thread in channel.threads:
#             await channel_thread.delete()
#
#     message_content = f"{user.mention}[.](https://imgur.com/1bS0ahP.png)"
#     thread_name = "⠀̛"
#
#     threads_to_create = [
#         channel.create_thread(
#             name=thread_name,
#             type=disnake.ChannelType.private_thread,
#             invitable=False
#         )
#         for _ in range(threads)
#     ]
#
#     created_threads = await asyncio.gather(*threads_to_create)
#
#     async def work(thread):
#         for _ in range(messages):
#             await thread.send(content=message_content)
#
#     tasks = [asyncio.create_task(work(thread)) for thread in created_threads]
#     await asyncio.gather(*tasks)
#
#     for thread in created_threads:
#         await thread.delete()

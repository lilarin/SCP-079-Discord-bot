import asyncio
import io
import random

import asyncpg
import disnake
from disnake.ext import commands

from app.config import config, logger
from app.modals.dossier_modal import DossierModal
from app.models import User
from app.services.articles_service import article_service
from app.services.keycard_service import keycard_service
from app.services.leaderboard_service import leaderboard_service
from app.services.scp_objects_service import scp_objects_service
from app.utils.articles_utils import article_utils
from app.utils.keycard_utils import keycard_utils
from app.utils.leaderboard_utils import leaderboard_utils
from app.utils.response_utils import response_utils
from app.utils.time_utils import time_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
    await scp_objects_service.update_scp_objects()
    timestamp = await time_utils.get_normalised()
    logger.info(f"[{timestamp}] Виконано вхід як {bot.user}")
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
    timestamp = await time_utils.get_normalised()
    logger.info(f"[{timestamp}] Користувач {user} використав команду /{command}")


@bot.event
async def on_slash_command_error(interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await response_utils.send_ephemeral_response(interaction, "Ця команда недоступна для вас")
        return

    timestamp = await time_utils.get_normalised()
    logger.error(f"[{timestamp}] {error}")


@bot.event
async def on_member_join(member):
    template = config.templates[-1]

    user_name = await keycard_utils.process_username(member.display_name)
    user_code = await keycard_utils.get_user_code(member.joined_at.timestamp())
    avatar = io.BytesIO(await member.avatar.read())
    avatar_decoration = member.avatar_decoration
    if avatar_decoration:
        avatar_decoration = io.BytesIO(await avatar_decoration.read())

    card = await asyncio.to_thread(
        keycard_service.process_template,
        template.image,
        user_name,
        user_code,
        avatar,
        template.primary_color,
        template.secondary_color,
        avatar_decoration,
    )

    embed = await keycard_utils.format_new_user_embed(member.mention, card, template.embed_color)

    await member.guild.system_channel.send(embed=embed)

    try:
        await User.get_or_create(user_id=member.id)
    except asyncpg.exceptions.InternalServerError as exception:
        timestamp = await time_utils.get_normalised()
        logger.error(f"[{timestamp}] {exception}")


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

    template = config.templates[random.randint(0, len(config.templates) - 1)]

    user_name = await keycard_utils.process_username(member.display_name)
    user_code = await keycard_utils.get_user_code(member.joined_at.timestamp())
    avatar = io.BytesIO(await member.avatar.read())
    avatar_decoration = member.avatar_decoration
    if avatar_decoration:
        avatar_decoration = io.BytesIO(await avatar_decoration.read())

    image = await asyncio.to_thread(
        keycard_service.process_template,
        template.image,
        user_name,
        user_code,
        avatar,
        template.primary_color,
        template.secondary_color,
        avatar_decoration,
    )

    try:
        db_user, created = await User.get_or_create(user_id=member.id)
        top_role = member.top_role

        embed = await keycard_utils.format_user_embed(
            card=image,
            color=template.embed_color,
            dossier=db_user.dossier if not created else None,
            role=top_role if top_role != member.guild.default_role else None,
        )

        await response_utils.send_response(interaction, embed=embed)

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання користувача")
        timestamp = await time_utils.get_normalised()
        logger.error(f"[{timestamp}] {exception}")


@bot.slash_command(name="випадкова-стаття", description="Отримати посилання на випадкову статтю за фільтрами")
async def get_random_article(
        interaction: disnake.ApplicationCommandInteraction,
        object_class=commands.Param(
            choices=list(config.scp_classes.keys()), description="Клас об'єкту (необов'язково)", default=None
        ),
        object_range=commands.Param(
            choices=list(config.scp_ranges.keys()), description="Діапазон номеру об'єкту (необов'язково)", default=None
        ),
        skip_viewed: bool = commands.Param(
            choices=[True, False], description="Виключити вже переглянуті? (необов'язково, увімкнено)", default=True
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
        timestamp = await time_utils.get_normalised()
        logger.error(f"[{timestamp}] {exception}")


@bot.slash_command(name="досьє", description="Заповнити своє досьє")
async def view_card(interaction: disnake.ApplicationCommandInteraction):
    try:
        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        await interaction.response.send_modal(
            modal=DossierModal(user=interaction.user, db_user=db_user)
        )
    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.wait_for_ephemeral_response(interaction, "Виникла помилка під час отримання користувача")
        timestamp = await time_utils.get_normalised()
        logger.error(f"[{timestamp}] {exception}")


@bot.slash_command(name="топ", description="Показати топ користувачів за певним критерієм")
async def top_articles(
        interaction: disnake.ApplicationCommandInteraction,
        criteria=commands.Param(
            choices=list(["Переглянуті статті", "Баланс", "Репутація"]), description="Критерій для перегляду списку лідерів"
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        if criteria == "Переглянуті статті":
            top_users = await leaderboard_service.get_articles_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за переглянутими статтями",
                hint="Кількість унікальних статей, що були переглянуті користувачем",
                symbol="📚",
                color="#f5575a"
            )
            await response_utils.send_response(interaction, embed=embed)
        elif criteria == "Баланс":
            top_users = await leaderboard_service.get_balance_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за поточною репутацією у фонді",
                hint="Поточний баланс користувача, що може зменшитись за різних дій",
                symbol="💠",
                color="#57b1f5"
            )
            await response_utils.send_response(interaction, embed=embed)
        elif criteria == "Репутація":
            top_users = await leaderboard_service.get_reputation_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за загальною репутацією у фонді",
                hint="Загальна репутація користувача, що була зароблена за весь час",
                symbol="🔰",
                color="#FFD700"
            )
            await response_utils.send_response(interaction, embed=embed)

    except Exception as e:
        await response_utils.send_response(interaction, "Виникла помилка під час отримання топу.")
        timestamp = await time_utils.get_normalised()
        logger.error(f"[{timestamp}] {e}")


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

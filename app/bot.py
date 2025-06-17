import asyncio
import io
import random

import disnake
from disnake.ext import commands

from app.config import config, logger
from app.services.keycard_service import keycard_service
from app.utils.keycard_utils import keycard_utils
from app.utils.response_utils import response_utils
from app.utils.time_utils import time_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
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
async def on_member_join(member):
    template = config.templates[-1]

    user_name = await keycard_utils.process_username(member.display_name)
    user_code = await keycard_utils.get_user_code(member.joined_at.timestamp())
    avatar = io.BytesIO(await member.avatar.read())
    avatar_decoration = member.avatar_decoration
    if avatar_decoration:
        avatar_decoration = io.BytesIO(await avatar_decoration.read())

    card = await keycard_service.process_template(
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


@bot.slash_command(name="картка", description="Переглянути картку співробітника фонду")
async def view_card(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача", default=None),
):
    await response_utils.wait_for_response(interaction)

    if not user:
        user = interaction.user

    template = config.templates[random.randint(0, len(config.templates) - 1)]

    user_name = await keycard_utils.process_username(user.display_name)
    user_code = await keycard_utils.get_user_code(user.joined_at.timestamp())
    avatar = io.BytesIO(await user.avatar.read())
    avatar_decoration = user.avatar_decoration
    if avatar_decoration:
        avatar_decoration = io.BytesIO(await avatar_decoration.read())

    card = await keycard_service.process_template(
        template.image,
        user_name,
        user_code,
        avatar,
        template.primary_color,
        template.secondary_color,
        avatar_decoration,
    )

    embed = await keycard_utils.format_user_embed(card, template.embed_color)

    await response_utils.send_response(interaction, embed=embed)


@bot.event
async def on_slash_command_error(interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await response_utils.send_ephemeral_response(interaction, "Ця команда недоступна для вас")
        return


@bot.slash_command(name="пнути", description="???")
@commands.has_permissions(administrator=True)
async def spam(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="Оберіть користувача"),
        threads: int = commands.Param(
            description="Кількість гілок для надсилання повідомлень",
            default=25, max_value=25
        ),
        messages: int = commands.Param(
            description="Кількість надісланих повідомлень у кожній гілці",
            default=400, max_value=4000
        ),
        delete_existing_threads: bool = commands.Param(
            description="Видалити існуючі гілки в каналі?",
            default=False
        ),
):
    await response_utils.wait_for_ephemeral_response(interaction)

    channel_type = interaction.channel.type

    if channel_type != disnake.ChannelType.text:
        await response_utils.send_response(
            interaction,
            message=f"Команду можна використовувати лише в **текстових** каналах"
        )
        return

    if user.bot:
        await response_utils.send_response(
            interaction,
            message=f"Команду не можна використовувати на ботах"
        )
        return

    user_mention = user.mention

    await response_utils.send_response(
        interaction,
        message=f"{user_mention} поплачет"
    )

    channel = interaction.channel
    if delete_existing_threads:
        for channel_thread in channel.threads:
            await channel_thread.delete()

    message_content = f"{user_mention}[.](https://imgur.com/1bS0ahP.png)"
    thread_name = "⠀̛"

    threads_to_create = [
        channel.create_thread(
            name=thread_name,
            type=disnake.ChannelType.private_thread,
            invitable=False
        )
        for _ in range(threads)
    ]

    created_threads = await asyncio.gather(*threads_to_create)

    async def work(thread):
        for _ in range(messages):
            await thread.send(content=message_content)

    tasks = [asyncio.create_task(work(thread)) for thread in created_threads]
    await asyncio.gather(*tasks)

    for thread in created_threads:
        await thread.delete()


bot.run(config.discord_bot_token)

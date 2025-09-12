import asyncio

import asyncpg
import disnake
from disnake.ext import commands

from app.config import config, logger
from app.core.decorators import (
    target_is_user,
    remove_bet_from_balance,
    is_allowed_user
)
from app.core.models import User as UserModel
from app.localization import t
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
    achievement_handler_service,
    interaction_service
)
from app.utils.response_utils import response_utils
from app.utils.time_utils import time_utils
from app.utils.ui_utils import ui_utils

bot = commands.InteractionBot(intents=disnake.Intents.all())


@bot.event
async def on_ready():
    try:
        await economy_logging_service.init_logging(bot)
        if config.update_scp_objects:
            await scp_objects_service.update_scp_objects()
        if config.sync_shop_cards:
            await shop_service.sync_shop_cards()
        if config.sync_achievements:
            await achievement_service.sync_achievements()
    except asyncpg.exceptions.InternalServerError as exception:
        logger.error(exception)
    logger.info(t("logs.logged_in", bot_user=bot.user))
    await asyncio.sleep(1)
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.watching,
            name=t("presence.watching")
        )
    )


@bot.event
async def on_slash_command(interaction):
    user = interaction.user
    command = interaction.data.name
    logger.info(t("logs.command_used", user=user, command=command))


@bot.event
async def on_slash_command_error(interaction, error):
    if isinstance(error, commands.NoPrivateMessage):
        await response_utils.send_ephemeral_response(interaction, t("errors.no_private_message"))
    elif isinstance(error, disnake.ext.commands.errors.CommandOnCooldown):
        timestamp = await time_utils.get_current()
        timestamp = round(timestamp.timestamp() + error.retry_after)
        await response_utils.send_ephemeral_response(interaction, t("errors.cooldown", timestamp=timestamp))
        asyncio.create_task(achievement_handler_service.handle_cooldown_achievement(interaction.user))
    else:
        logger.error(error)


@bot.event
async def on_member_join(member):
    try:
        profile_data = await keycard_service.get_user_profile_data(member)

        embed = await ui_utils.format_new_user_embed(
            member.mention,
            profile_data.card_image,
            profile_data.card_template.embed_color
        )

        if member.guild.system_channel:
            await member.guild.system_channel.send(embed=embed)
        else:
            logger.warning(t("logs.system_channel_not_found", guild_name=member.guild.name))

    except asyncpg.exceptions.InternalServerError as error:
        logger.error(error)
    except Exception as exception:
        logger.error(exception)


@bot.slash_command(name=t("commands.view_card.name"), description=t("commands.view_card.description"))
@commands.guild_only()
@target_is_user
async def view_card(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(
            description=t("commands.view_card.params.user.description"),
            default=None,
            name=t("commands.view_card.params.user.name")
        ),
):
    await response_utils.wait_for_response(interaction)
    member = user or interaction.user

    try:
        try:
            target: disnake.Member = await interaction.guild.fetch_member(member.id)
        except disnake.NotFound:
            target: disnake.User = member

        profile_data = await keycard_service.get_user_profile_data(target)

        embed = await ui_utils.format_user_embed(
            card=profile_data.card_image,
            color=profile_data.card_template.embed_color,
            dossier=profile_data.dossier,
            role=profile_data.top_role,
            achievements_count=profile_data.achievements_count
        )

        await response_utils.send_response(interaction, embed=embed)
        asyncio.create_task(achievement_handler_service.handle_view_card_achievements(interaction.user, member))

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=1, per=config.article_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.get_random_article.name"),
                   description=t("commands.get_random_article.description"))
@commands.guild_only()
async def get_random_article(
        interaction: disnake.ApplicationCommandInteraction,
        object_class=commands.Param(
            choices=list(config.scp_classes.keys()),
            description=t("commands.get_random_article.params.object_class.description"),
            default=None, name=t("commands.get_random_article.params.object_class.name")
        ),
        object_range=commands.Param(
            choices=list(config.scp_ranges.keys()),
            description=t("commands.get_random_article.params.object_range.description"),
            default=None, name=t("commands.get_random_article.params.object_range.name")
        ),
        skip_viewed: bool = commands.Param(
            choices=[True, False],
            description=t("commands.get_random_article.params.skip_viewed.description"),
            default=True, name=t("commands.get_random_article.params.skip_viewed.name")
        )
):
    await response_utils.wait_for_response(interaction)

    try:
        found_all, random_article = await scp_objects_service.get_random_scp_object(
            user=interaction.user,
            object_class=config.scp_classes[object_class] if object_class else None,
            object_range=config.scp_ranges[object_range] if object_range else None,
            skip_viewed=skip_viewed,
        )

        if found_all:
            await response_utils.send_response(
                interaction, message=t("responses.articles.all_viewed"), delete_after=10
            )
        elif random_article:
            image = await article_service.create_article_image(random_article)

            embed, components = await ui_utils.format_article_embed(random_article, image)
            await response_utils.send_response(interaction, embed=embed, components=components)
        else:
            await response_utils.send_response(
                interaction, message=t("responses.articles.not_found"), delete_after=10
            )

    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.dossier.name"), description=t("commands.dossier.description"))
@commands.guild_only()
async def dossier(interaction: disnake.ApplicationCommandInteraction):
    try:
        db_user, _ = await UserModel.get_or_create(user_id=interaction.user.id)

        await interaction.response.send_modal(
            modal=DossierModal(user=interaction.user, db_user=db_user)
        )
    except asyncpg.exceptions.InternalServerError as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.top.name"), description=t("commands.top.description"))
@commands.guild_only()
async def top(
        interaction: disnake.ApplicationCommandInteraction,
        criteria=commands.Param(
            choices=list(config.leaderboard_options.keys()),
            description=t("commands.top.params.criteria.description"),
            name=t("commands.top.params.criteria.name")
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        chosen_criteria = config.leaderboard_options[criteria]
        embed, components = await leaderboard_service.init_leaderboard_message(bot, interaction.guild, chosen_criteria)
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.balance.name"), description=t("commands.balance.description"))
@commands.guild_only()
@target_is_user
async def balance(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(
            description=t("commands.balance.params.user.description"),
            default=None,
            name=t("commands.balance.params.user.name")
        ),
):
    await response_utils.wait_for_response(interaction)
    target_user = user or interaction.user

    try:
        embed = await economy_management_service.create_user_balance_message(target_user)
        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.transfer.name"), description=t("commands.transfer.description"))
@commands.guild_only()
async def transfer(
        interaction: disnake.ApplicationCommandInteraction,
        recipient: disnake.User = commands.Param(
            description=t("commands.transfer.params.recipient.description"),
            name=t("commands.transfer.params.recipient.name")
        ),
        amount: int = commands.Param(
            description=t("commands.transfer.params.amount.description"),
            name=t("commands.transfer.params.amount.name"),
            ge=100
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        try:
            target: disnake.Member = await interaction.guild.fetch_member(recipient.id)
        except disnake.NotFound:
            target: disnake.User = recipient

        success, message = await economy_management_service.transfer_balance(
            interaction.user, target, amount
        )
        if success:
            await response_utils.send_response(interaction, message)
        else:
            await response_utils.send_response(interaction, message, delete_after=10)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.shop.name"), description=t("commands.shop.description"))
@commands.guild_only()
async def shop(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)
    try:
        embed, components = await shop_service.init_shop_message()
        await response_utils.send_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.update_shop.name"), description=t("commands.update_shop.description"))
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def update_shop(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        await shop_service.update_card_item_quantities()
        await response_utils.edit_ephemeral_response(interaction, t("responses.shop.updated"))

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.buy.name"), description=t("commands.buy.description"))
@commands.guild_only()
async def buy(
        interaction: disnake.ApplicationCommandInteraction,
        item_id: str = commands.Param(
            description=t("commands.buy.params.item_id.description"),
            name=t("commands.buy.params.item_id.name")
        ),
):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        db_user, _ = await UserModel.get_or_create(user_id=interaction.user.id)

        message = await shop_service.buy_item(
            user=interaction.user,
            db_user=db_user,
            item_id=item_id
        )

        await response_utils.edit_ephemeral_response(interaction, message=message)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.inventory.name"), description=t("commands.inventory.description"))
@commands.guild_only()
async def inventory(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        db_user, _ = await UserModel.get_or_create(user_id=interaction.user.id)

        await inventory_service.check_for_default_card(user=db_user)

        embed, components = await inventory_service.init_inventory_message(user=interaction.user)
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.equip.name"), description=t("commands.equip.description"))
@commands.guild_only()
async def equip(
        interaction: disnake.ApplicationCommandInteraction,
        item_id: str = commands.Param(
            description=t("commands.equip.params.item_id.description"),
            name=t("commands.equip.params.item_id.name")
        ),
):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        await UserModel.get_or_create(user_id=interaction.user.id)

        message = await inventory_service.equip_item(
            user_id=interaction.user.id,
            item_id=item_id
        )

        await response_utils.edit_ephemeral_response(interaction, message=message)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=1, per=config.work_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.legal_work.name"), description=t("commands.legal_work.description"))
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
@bot.slash_command(name=t("commands.risky_work.name"), description=t("commands.risky_work.description"))
@commands.guild_only()
async def risky_work(interaction: disnake.ApplicationCommandInteraction):
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


@bot.slash_command(name=t("commands.reset_reputation.name"), description=t("commands.reset_reputation.description"))
@commands.guild_only()
@is_allowed_user
async def reset_reputation(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)

    try:
        await economy_management_service.reset_users_reputation()
        await response_utils.send_response(
            interaction, t("responses.reputation.reset")
        )

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.edit_balance.name"), description=t("commands.edit_balance.description"))
@commands.guild_only()
@is_allowed_user
@target_is_user
async def edit_player_balance(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(
            description=t("commands.edit_balance.params.user.description"),
            name=t("commands.edit_balance.params.user.name")
        ),
        amount: int = commands.Param(
            description=t("commands.edit_balance.params.amount.description"),
            name=t("commands.edit_balance.params.amount.name")
        ),
):
    await response_utils.wait_for_response(interaction)

    try:
        reason = t("responses.balance.admin_change_reason", user=interaction.user.mention)
        await economy_management_service.update_user_balance(
            user, amount, reason, balance_only=True
        )

        await response_utils.send_response(
            interaction, t("responses.balance.changed", user=user.mention)
        )

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.game_crystallize.name"), description=t("commands.game_crystallize.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_crystallize(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_crystallize.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_crystallize.params.bet.name")
        ),
):
    try:
        await crystallization_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.game_coin.name"), description=t("commands.game_coin.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_coin_flip(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_coin.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_coin.params.bet.name")
        ),
):
    try:
        await coin_flip_service.play_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.game_candy.name"), description=t("commands.game_candy.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_candy(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_candy.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_candy.params.bet.name")
        ),
):
    try:
        await candy_game_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.game_coguard.name"), description=t("commands.game_coguard.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_coguard(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_coguard.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_coguard.params.bet.name")
        ),
):
    try:
        await coguard_service.start_game(interaction, bet)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@bot.slash_command(name=t("commands.game_scp173.name"), description=t("commands.game_scp173.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_scp173(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_scp173.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_scp173.params.bet.name")
        ),
        mode: str = commands.Param(
            description=t("commands.game_scp173.params.mode.description"),
            choices={
                t("commands.game_scp173.params.mode.choices.normal"): "normal",
                t("commands.game_scp173.params.mode.choices.lms"): "last_man_standing"
            },
            name=t("commands.game_scp173.params.mode.name")
        )
):
    try:
        await staring_game_service.start_lobby(interaction, bet, mode)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@commands.cooldown(rate=config.games_cooldown_rate, per=config.games_cooldown_time_minutes * 60, type=config.cooldown_type)
@bot.slash_command(name=t("commands.game_hole.name"), description=t("commands.game_hole.description"))
@commands.guild_only()
@remove_bet_from_balance
async def game_hole(
        interaction: disnake.ApplicationCommandInteraction,
        bet: int = commands.Param(
            description=t("commands.game_hole.params.bet.description"),
            ge=100, le=10000,
            name=t("commands.game_hole.params.bet.name")
        ),
        group_bet: str = commands.Param(
            description=t("commands.game_hole.params.group_bet.description"),
            choices=list(config.hole_group_bet_options.keys()),
            default=None,
            name=t("commands.game_hole.params.group_bet.name")
        ),
        item_bet: str = commands.Param(
            description=t("commands.game_hole.params.item_bet.description"),
            autocomplete=hole_game_service.item_autocomplete,
            default=None,
            name=t("commands.game_hole.params.item_bet.name")
        )
):
    if (group_bet and item_bet) or (not group_bet and not item_bet):
        reason = t("responses.games.invalid_bet_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )
        await response_utils.send_response(
            interaction, t("responses.games.hole.choose_one_bet_type"), delete_after=10
        )
        return

    if item_bet and item_bet not in config.hole_items.values():
        reason = t("responses.games.invalid_bet_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )
        await response_utils.send_response(
            interaction, t("responses.games.hole.option_not_found", option=item_bet), delete_after=10
        )
        return

    choice = group_bet or item_bet

    try:
        if hole_game_service.is_game_active(interaction.channel.id):
            await hole_game_service.join_game(interaction, bet, choice)
        else:
            await hole_game_service.create_game(interaction, bet, choice)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)
        reason = t("responses.games.error_refund", command=interaction.data.name)
        await economy_management_service.update_user_balance(
            interaction.user, bet, reason
        )


@bot.slash_command(name=t("commands.games_info.name"), description=t("commands.games_info.description"))
@commands.guild_only()
async def games_info(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_response(interaction)
    try:
        embed = await ui_utils.format_games_info_embed()
        await response_utils.send_response(interaction, embed=embed)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.achievements.name"), description=t("commands.achievements.description"))
@commands.guild_only()
@target_is_user
async def achievements(
        interaction: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(
            description=t("commands.achievements.params.user.description"),
            default=None,
            name=t("commands.achievements.params.user.name")
        ),
):
    await response_utils.wait_for_ephemeral_response(interaction)
    user = user or interaction.user

    try:
        try:
            target: disnake.Member = await interaction.guild.fetch_member(user.id)
        except disnake.NotFound:
            target: disnake.User = user

        embed, components = await achievement_service.init_achievements_message(target)
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)

    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.slash_command(name=t("commands.achievement_stats.name"), description=t("commands.achievement_stats.description"))
@commands.guild_only()
async def achievement_stats(interaction: disnake.ApplicationCommandInteraction):
    await response_utils.wait_for_ephemeral_response(interaction)

    try:
        embed, components = await achievement_service.init_stats_message()
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)
    except Exception as exception:
        await response_utils.send_error_response(interaction)
        logger.error(exception)


@bot.event
async def on_button_click(interaction: disnake.MessageInteraction) -> None:
    try:
        await interaction_service.handle_button_click(bot, interaction)
    except Exception as exception:
        logger.error(exception)

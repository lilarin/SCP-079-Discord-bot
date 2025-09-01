# SCP-079 Discord Bot

Welcome to the repository for the SCP-079 Discord Bot, a comprehensive economy and entertainment bot themed around the
SCP Foundation universe. This bot integrates deep progression systems, interactive mini-games, and extensive
customization and competition options to create an engaging community experience

## Features

### Essentials

* **Dynamic user profiles as keycards:** Every user receives a unique "Keycard" profile. This profile displays their
  rank, server role, balance, achievements, and a customizable dossier. The visual design of the keycard dynamically
  updates when the user equips different high-level access cards
* **Narrative work system:** Earn currency through work prompts that are presented as mini-stories. Choose between "
  Legal Work" for a safe, guaranteed income, or "Risky Work" for a chance at a much larger reward or a significant
  penalty. The complexity and payout of these stories evolve as you acquire better keycards
* **Deep progression & achievements:** Unlock unique achievements by participating in games, exploring SCP articles,
  engaging with the economy, and progressing through the ranks. Certain high-tier items in the shop can only be
  purchased after unlocking specific prerequisite achievements
* **SCP article explorer:** Discover new SCPs directly within Discord. The bot can fetch random articles from the SCP
  Wiki, allowing you to filter by object class (Safe, Euclid, Keter, etc.) and series number. It even generates a custom
  preview image for each article
* **Shop & inventory system:** Use your earnings to purchase new keycards and other items from the server shop. Manage
  your collection in your inventory and choose which keycard to equip and display on your profile
* **Competitive leaderboards:** Track your progress against other server members on leaderboards for wealth, total
  reputation earned, achievements unlocked, and articles discovered

### Mini-Games

* **Crystallization (crash):** Place a bet and watch your multiplier grow. The longer you let it crystallize, the higher
  the potential payout, but the risk of losing everything increases with every step. Cash out before the crystal
  shatters!
* **Coguard (higher or lower):** A test of cognitive resilience. Guess whether the next randomly generated number will
  be higher or lower than the current one. Build up your win streak to increase your payout multiplier
* **SCP–173 staring (russian roulette analog):** Join a lobby with other players and try to survive rounds of "
  blinking." In each round, players have a chance of being eliminated. Be the last one standing to win the entire pot.
  Supports "Normal Mode" (game ends on first elimination) and "Last Man Standing Mode."
* **SCP–330 candy game (risk management):** Inspired by SCP-330 "Take Only Two." You start with an unknown number of
  pre-taken candies. Each candy you take increases your potential reward, but if the total number of candies taken
  exceeds the limit, you lose your entire bet
* **The hole (roulette):** A timed-lobby roulette game where players bet on which anomalous item "The Hole" will return.
  Place high–risk bets on specific items (36x payout) or safer bets on item categories (2x or 3x payout)
* **Coin flip:** The classic 50/50 chance to double your bet. Quick, simple, and risky

> [!IMPORTANT]
> ### [Demonstration (Imgur screenshots collection)](https://imgur.com/a/lilarin-scp-079-discord-bot-kafjgyl)
> <details>
>   <summary><b>Slash Commands</b></summary></br>
>
> ### General Commands
>
> * `/achievements-list` – Show the list and statistics of achievements on the server.
> * `/dossier` – Fill out your dossier.
> * `/games-guide` – Information about available mini–games.
> * `/random-article` – Get a link to a random article with filters.
> * `/top` – Show the top users by a specific criterion.
> * `/user-achievements` – Show the earned achievements.
>
> ### Economy Commands
>
> * `/balance` – View a user's balance.
> * `/buy` – Buy an item from the shop by its ID.
> * `/card` – View a foundation employee's card.
> * `/equip` – Equip an access card from your inventory.
> * `/inventory` – View your inventory.
> * `/job` – Perform a safe task for the foundation.
> * `/risky-job` – Take on a risky task.
> * `/shop` – View items in the shop.
> * `/transfer` – Send your own 💠 to another user.
>
> ### Game Commands
>
> * `/candies` – Test your luck with SCP–330.
> * `/cognitive-resistance` – Pass the cognitive resistance test.
> * `/coin` – Flip a coin and test your luck.
> * `/crystallization` – Start the crystallization process.
> * `/hole` – Place a bet in the anomalous roulette.
> * `/peekaboo` – Play peekaboo against other players with SCP–173.
>
> ### Admin Commands
>
> * `/change-user-balance` – Increase or decrease the balance by a certain amount of reputation.
> * `/reset-reputation` – Reset the total reputation of all employees.
> * `/update-item-quantity` – Randomly update the assortment of cards in the shop.
>
> </details>

---

## Technical Overview & Setup Guide

### Technology Stack

* **Core:** `disnake`
* **Database:** `PostgreSQL`
* **Data scrapping:** `BeautifulSoup4`
* **ORM:** `tortoise-orm` with `asyncpg` driver
* **Image processing and caching:** `Pillow` for generating keycards and article previews

### Installation and Setup

1. **Clone the repository**

2. **Create a virtual environment and install dependencies:**
   ```bash
   python –m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install –r requirements.txt
   ```

3. **Environment variables configuration:**

   Rename the `.env.example` file and fill in the required credentials.

4. **Database migration:**
   The project uses `aerich` for database migrations with Tortoise ORM. Run the following command to init the database:
   ```bash
   aerich init –t app.config.tortoise_orm
   ```

5. **Initial data population:**
   On the first run, ensure the configuration flags in your `.env` file are set to `True` to populate the database with
   initial data:
    * `UPDATE_SCP_OBJECTS=True`: Runs the scraper to fetch SCP articles from the wiki.
    * `SYNC_SHOP_CARDS=True`: Populates the `items` table based on `assets/configs/shop_cards.json`.
    * `SYNC_ACHIEVEMENTS=True`: Populates the `achievements` table based on `assets/configs/achievements.json`.
      After the first successful launch, you can set these flags to `False` to speed up subsequent restarts.

6. **Run the bot:**
   ```bash
   python –m app.main
   ```
   or on Windows, run using `start_bot.bat`

---

## Disclaimers

> [!IMPORTANT]
> ### Designs
> The image assets included in this repository serve as **layout templates only**. They are provided to demonstrate the
> correct dimensions and positioning required for text and image overlays
>
> **The final visual designs used in my production bot are not included in this public repository!**
>
> ### The Specifics of The Scraper
> The web scraper is **specifically designed to work with HTML structure of
the [Ukrainian SCP Wiki](http://scp-ukrainian.wikidot.com/)**. It relies on specific CSS selectors and page layouts
> found on that site to correctly parse SCP object numbers, titles, and classes
>
> **This scraper will not work out–of–the–box with other SCP wikis (e.g., English, Polish, etc.)**, to adapt the bot for
> a different wiki, you will need to:
> 1. Analyze the HTML structure of SCP Series" pages on your target wiki
> 2. Modify the parsing logic in `_parse_scp_data` method to match the new structure
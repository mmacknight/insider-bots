# Insider Bots

## Overview

Insider Bots is a Python project that creates a Twitter bot reporting on your fantasy football league. The bot reports rumors and transactions happening in the league using Twitter and Sleeper APIs. The project allows users to submit rumors to a Twitter account via Direct Messages, which are then automatically reported on the same account. The project also uses Sleeper APIs to report on various transactions, including player signings, trades, and waiver claims.

## Setup

To use Insider Bots, you'll need to set up a few things first:

1. Clone this repository to your local machine.
2. Set up a Twitter developer account and create a new app to obtain API credentials.
3. Set up a separate Twitter account which will serve a the reporter bot for your league.
4. Use the auth.py file to generate an access token and secret for the bot account.
5. Create a `.env` file in the root directory of the project with the following environment variables:
```
MODE = <PROD or DEV>
LEAGUE_ID = <ID of the Sleeper fantasy football league>

# DEVELOPER ACCOUNT PARAMETERS
API_KEY = <your API key>
SECRET = <your API secret key>

#BOT ACCOUNT PARAMETERS
BEARER_TOKEN = <your bearer token>
ACCESS_TOKEN = <your access token (if in production mode)>
ACCESS_TOKEN_SECRET = <your access token secret (if in production mode)>
DEV_ACCESS_TOKEN = <your development access token (if in development mode)>
DEV_ACCESS_TOKEN_SECRET = <your development access token secret (if in development mode)>

# HOW OFTEN THE BOT CHECKS FOR UPDATES, RECOMMEND SETTING TO 1 MINUTE
RESET_PERIOD_HOUR = <number of hours between reset periods>
RESET_PERIOD_MINUTE = <number of minutes between reset periods>
RESET_PERIOD_SECOND = <number of seconds between reset periods>
```
6. Install the required Python packages by running `pip install -r requirements.txt` in the root directory of the project.
7. Run the project by running `python main.py` in the root directory of the project.

## Usage

This script periodically checks Sleeper APIs for recent league activity and direct messages from users following the bot. The interval of the periodic checks is determined by the RESET_PERIOD_HOUR, RESET_PERIOD_MINUTE, and RESET_PERIOD_SECOND environment variables specified in the .env file.

When the script is executed, it will report any transactions to a Twitter account associated with the ACCESS TOKEN specified in the .env file. The script also periodically tweets rumors collected from the DMs received in the format mentioned above. You must follow the bot before the previous reset period and then DM the bot with the format "RUMOR \<rumor\>" in order for the bot to report on your rumor.

To run the script, simply navigate to the project directory and run python main.py in the command line.


import os
import requests
import json
import time
import datetime
import tweepy
from dotenv import load_dotenv
import datetime
import tweepy
import random
import re

class Reporter:
    def __init__(self, config):
        """
        Initialize a new Reporter object.
        
        Args:
            config (dict): A dictionary containing configuration values.
        """
        # Set the initial state of the object.
        self.league_id = config["LEAGUE_ID"]
        self.transactions = []
        self.transaction_count = 0
        self.roster_lookup = {}
        self.user_lookup = {}
        self.teamLookup = {}
        self.id = ""
        self.scan_count = 0
        self.reset_count = config["RESET_COUNT"]
        self.indicator = config["INDICATOR"]

        # Create a new Tweepy client using the provided API keys and tokens.
        self.client = tweepy.Client(
            consumer_key=config["CONSUMER_KEY"], consumer_secret=config["CONSUMER_SECRET"],
            access_token=config["ACCESS_TOKEN"], access_token_secret=config["ACCESS_TOKEN_SECRET"]
        )

        # Load league and player data from the Sleeper API.
        self.load_league()
        self.load_players()

        # Load rosters, users, and transactions from the Sleeper API.
        self.load_rosters()
        self.load_users()
        self.load_transactions(init=True)

        # Get information about the current reporter bot and its followers.
        self.get_me()
        self.load_followers()

    def scan(self):
        """
        Continuously scan for new transactions and rumors.
        """
        while True and self.reset_count > self.scan_count:
            try:
                total_seconds = 24*3600 / self.reset_count

                # Wait for the specified amount of time between scans.
                while total_seconds > 0:
                    timer = datetime.timedelta(seconds = total_seconds)
                    print(f"Scan count: {self.scan_count}/{self.reset_count}. Next scan in: {timer}",end="\r")
                    time.sleep(1)
                    total_seconds -= 1

                print(f"Scan count: {self.scan_count}/{self.reset_count}. Next scan in: {timer}",end="\r")

                # Check for new transactions and rumors.
                new_transaction_count = self.load_transactions()
                new_dm_count = self.scan_dms()
                current_timestamp = datetime.datetime.now()
                print(f"Reported {new_transaction_count} new / {self.transaction_count} total transactions - {current_timestamp}\nReported {new_dm_count} rumors - {current_timestamp}\n", end="\r")

                self.scan_count += 1
            except Exception as e:
                print(f"Error occured: {e}")

    def tweet(self,text):
        """
        Post a new tweet using the Tweepy client.

        Args:
            text (str): The text of the tweet.
        """
        self.client.create_tweet(text=text)

    def load_league(self):
        """
        Load data about the current league from the Sleeper API.
        """
        resp = requests.get(f'https://api.sleeper.app/v1/league/{self.league_id}')
        self.league = json.loads(resp.text)
  
    def load_players(self):
        """
        Load data about NFL players from the Sleeper API.
        """
        resp = requests.get(f'https://api.sleeper.app/v1/players/nfl')
        self.players = json.loads(resp.text)

    def load_rosters(self):
        """
        Load data about the current rosters from the Sleeper API.
        """
        resp = requests.get(f'https://api.sleeper.app/v1/league/{self.league_id}/rosters')
        self.rosters = json.loads(resp.text)
        for roster in self.rosters:
            self.roster_lookup[roster["roster_id"]] = roster
            self.roster_lookup[roster["owner_id"]] = roster

    def load_users(self):
        """
        Loads the users of the league and sets the class attributes 'users' and 'user_lookup'.
        """
        resp = requests.get(f'https://api.sleeper.app/v1/league/{self.league_id}/users')
        self.users = json.loads(resp.text)
        self.user_lookup = {user["user_id"]: user for user in self.users}

    def load_transactions(self, init=False):
        """
        Load the transactions of the league from Sleeper API and sets the class attributes 'transactions' and 'transaction_count'.
        
        Args:
            init (bool, optional): If True and there are new transactions since the last time this method was called, it calls the appropriate 
                        reporting method for each new transaction.

        Returns:
            int: Number of new transactions since the last time this method was called.
        """
        new_transaction_count = 0

        # Fetch transactions from Sleeper API for all 20 weeks
        self.transactions = []
        for week in range(20):
            resp = requests.get(f'https://api.sleeper.app/v1/league/{self.league_id}/transactions/{week}')
            self.transactions.extend(json.loads(resp.text))
        
        # Sort the transactions by status_updated timestamp
        def get_status(t):
            return t["status_updated"]
        self.transactions.sort(key=get_status)
        
        # Count new transactions since the last time this method was called
        new_transaction_count = len(self.transactions) - self.transaction_count
        self.transaction_count = len(self.transactions)

        # If init is False and there are new transactions, report each new transaction by calling the appropriate reporting method
        if not init and new_transaction_count > 0:
            index = -1 * new_transaction_count
            for transaction in self.transactions[(index+self.transaction_count):self.transaction_count]:
                try:
                    if transaction["type"] == "trade":
                        self.report_trade(transaction)
                    elif transaction["type"] == "free_agent":
                        self.report_free_agent(transaction)
                    elif transaction["type"] == "waiver" and transaction["status"] == "complete":
                        self.report_waiver(transaction)
                except Exception as e:
                    if transaction["type"] == "trade":
                        print(self.report_trade(transaction, False))
                    elif transaction["type"] == "free_agent":
                        print(self.report_free_agent(transaction, False))
                    elif transaction["type"] == "waiver" and transaction["status"] == "complete":
                        print(self.report_waiver(transaction, False))
                    print(f"Transaction error occurred: {e}")

        return new_transaction_count

    def format_player(self, player):
        """
        Returns a formatted string that describes the specified player.

        Args:
            player (dict): A dictionary containing information about the player.

        Returns:
            str: A formatted description of the player.
        """
        return f"{player['team']} {player['fantasy_positions'][0]} {player['full_name']}"

    def format_pick(self, pick):
        """
        Returns a formatted string that describes the specified draft pick.

        Args:
            player (dict): A dictionary containing information about the draft pick.

        Returns:
            str: A formatted description of the draft pick.
        """
        post = "th"
        if pick["round"] == 1:
            post = "st"
        elif pick["round"] == 2:
            post = "nd"
        elif pick["round"] == 3:
            post = "rd"
        return f"a {pick['season']} {pick['round']}{post} round draft pick"

    def format_array(self,array):
        """
        Formats an array of items into a human-readable list.

        Args:
            array (list): A list of items to be formatted.

        Returns:
            str: A string containing the formatted list of items.
        """
        delim = ' and '
        if (len(array) > 2):
            array[-1] = ' and ' + array[-1]
            delim = ', '
        return delim.join(array)

    def report_trade(self,trade,tweet=True):
        """
        Generates a trade report based on the given trade and tweets it if `tweet` is True.

        Args:
            trade (dict): a dictionary containing details about the trade, including adds and draft picks.
            tweet (bool, optional): a boolean indicating whether to tweet the report. Default is True.

        Returns:
            str: a string containing the generated trade report.
        """

        tradeSides  = {}
        reportText = "Trade Alert!\n"
        for k,v in trade["adds"].items():
            if self.user_lookup[self.roster_lookup[v]["owner_id"]]["metadata"]["team_name"] not in tradeSides:
                tradeSides[self.user_lookup[self.roster_lookup[v]["owner_id"]]["metadata"]["team_name"]] = []
            tradeSides[self.user_lookup[self.roster_lookup[v]["owner_id"]]["metadata"]["team_name"]] += [self.format_player(self.players[k])]

        for pick in trade["draft_picks"]:
            if self.user_lookup[self.roster_lookup[pick["owner_id"]]["owner_id"]]["metadata"]["team_name"] not in tradeSides:
                tradeSides[self.user_lookup[self.roster_lookup[pick["owner_id"]]["owner_id"]]["metadata"]["team_name"]] = []
            tradeSides[self.user_lookup[self.roster_lookup[pick["owner_id"]]["owner_id"]]["metadata"]["team_name"]] += [self.format_pick(pick)]

        for team, stuff in tradeSides.items():
            reportText += (f"{team} will receive {self.format_array(stuff)}.\n")

        if tweet:
            self.tweet(reportText)
        return reportText

    def report_free_agent(self, transaction, tweet=True):
        """
        Generates a report for a free agency transaction and optionally sends it as a tweet.

        Args:
            transaction (dict): The transaction object.
            tweet (bool, optional): If True, the report will be tweeted. Defaults to True.

        Returns:
            str: The generated report text.

        """
        adds = []
        drops = []
        
        # Collects added players' names
        if transaction["adds"] is not None:
            for player in transaction["adds"]:
                adds.append(self.format_player(self.players[player]))

        # Collects dropped players' names
        if transaction["drops"] is not None:
            for player in transaction["drops"]:
                drops.append(self.format_player(self.players[player]))

        team = self.user_lookup[transaction["creator"]]["metadata"]["team_name"]

        adds = self.format_array(adds)
        drops = self.format_array(drops)
        reportText = ""
        
        # Generates report text based on the type of transaction
        if len(adds) and len(drops):
            reportText = f"{team} has signed {adds} and released {drops}."
        elif len(adds):
            reportText = f"{team} has signed {adds}."
        elif len(drops):
            reportText = f"{team} has released {drops}."
            
        # Tweets the report if tweet parameter is True
        if tweet:
            self.tweet(reportText)
        
        return reportText

    def report_waiver(self, transaction, tweet=True):
        """
        Generates a report for a waiver transaction and optionally sends it as a tweet.

        Args:
            transaction (dict): The transaction object.
            tweet (bool, optional): If True, the report will be tweeted. Defaults to True.

        Returns:
            str: The generated report text.

        """
        adds = []
        drops = []
        
        # Collects added players' names
        if transaction["adds"] is not None:
            for player in transaction["adds"]:
                adds.append(self.format_player(self.players[player]))

        # Collects dropped players' names
        if transaction["drops"] is not None:
            for player in transaction["drops"]:
                drops.append(self.format_player(self.players[player]))

        team = self.user_lookup[transaction["creator"]]["metadata"]["team_name"]

        adds = self.format_array(adds)
        drops = self.format_array(drops)
        reportText = ""
        
        # Generates report text based on the type of transaction
        if len(adds) and len(drops):
            reportText = f"{team} has claimed {add} from waivers and released {drops}."
        elif len(adds):
            reportText = f"{team} has claimed {adds} from waivers."
        elif len(drops):
            reportText = f"{team} has released {drops}."
            
        # Tweets the report if tweet parameter is True
        if tweet:
            self.tweet(reportText)
        
        return reportText

    def parse_dm(self,dm):
        """
        Parses a direct message and extracts the rumor if it matches the specified format.

        Args:
            dm (str): The text of the direct message.

        Returns:
            tuple: A tuple containing the string "RUMOR" and the rumor text if the direct message matches the specified format. Otherwise, 
            returns a tuple containing None, None.
        """
        m = re.match(r'RUMOR (?P<rumor>.*)', dm, re.IGNORECASE)
        if m != None:
            try:
                rumor = m.group('rumor')
                return ("RUMOR",rumor)
            except (AttributeError, ValueError):
                return (None, None)

    def load_followers(self):
        """
        Loads the followers of the Twitter user and sets the class attribute 'teamLookup'.
        """
        try:
            followers = self.client.get_users_followers(id=self.id,user_auth=True).data
            if (followers) :
                for user in self.client.get_users_followers(id=self.id,user_auth=True).data:
                    self.teamLookup[user.id] = user.name
        except Exception as e:
            print(e)

    def scan_dms(self):
        """
        Scans the direct messages of the Twitter user's followers and posts a tweet based on any matching rumors.

        Returns:
            int: The number of direct messages processed.
        """
        dm_count = 0
        for id in self.teamLookup:
            response = self.client.get_direct_message_events(participant_id=id,expansions=["sender_id","referenced_tweets.id","attachments.media_keys","participant_ids"])
            received = []

            if response == None or response.data == None:
                continue

            for dm in response.data:
                if self.indicator in dm.text:
                    break
                else:
                    received = [dm.text]+received

            if len(received):
                self.client.create_direct_message(participant_id=id,text=f"Got it! {self.indicator}")

            for message in received:
                try:
                    type,rumor = self.parse_dm(message)
                except Exception as e:
                    print("Error parsing DM",e)
                    continue
                
                phrase_bank = [
                    f"Anonymous sources are telling me \"{rumor}\"",
                    f"A source within the league is telling me \"{rumor}\"",
                    f"Sources within the league are telling me \"{rumor}\"",
                    f"An anonymous source has told me \"{rumor}\"",
                    "An anonymous source is telling me \"{rumor}\"",
                    f"Sources are telling me \"{rumor}\"",
                    f"A reliable source has told me \"{rumor}\"",
                    f"A reliable source has told me \"{rumor}\"",
                ]
                self.client.create_tweet(text=phrase_bank[random.randint(0,len(phrase_bank)-1)])
                dm_count += 1
        return dm_count

    def get_me(self):
        """
        Gets the user ID of the Twitter user and sets the class attribute 'id'.
        """
        self.id = self.client.get_me().data.id

if __name__ == "__main__":

    load_dotenv()

    MODE = os.getenv('MODE')

    HOUR = int(os.getenv('RESET_PERIOD_HOUR'))
    MINUTE = int(os.getenv('RESET_PERIOD_MINUTE'))
    SECOND = int(os.getenv('RESET_PERIOD_SECOND'))
     
    CONFIG = {}
    CONFIG['BEARER_TOKEN'] = os.getenv('BEARER_TOKEN')
    CONFIG['CONSUMER_KEY'] = os.getenv('API_KEY')
    CONFIG['CONSUMER_SECRET'] = os.getenv('SECRET')
    CONFIG['INDICATOR'] = '--##--'
    CONFIG["LEAGUE_ID"] = os.getenv('LEAGUE_ID')
    CONFIG["RESET_COUNT"] = int((24 *3600) / (HOUR * 3600 + MINUTE * 60 + SECOND))

    if MODE == "PROD":
        CONFIG["ACCESS_TOKEN"] = os.getenv('ACCESS_TOKEN')
        CONFIG["ACCESS_TOKEN_SECRET"] = os.getenv('ACCESS_TOKEN_SECRET')
    else:
        CONFIG["ACCESS_TOKEN"] = os.getenv('DEV_ACCESS_TOKEN')
        CONFIG["ACCESS_TOKEN_SECRET"] = os.getenv('DEV_ACCESS_TOKEN_SECRET')

    ERROR_COUNT = 0

    while True and ERROR_COUNT < 20:
        print(f"RESETING REPORTER - EC: {ERROR_COUNT}")
        try:
            reporter = Reporter(CONFIG)
            ERROR_COUNT = 0
            reporter.scan()
        except Exception as e:
            ERROR_COUNT += 1
            print(e)

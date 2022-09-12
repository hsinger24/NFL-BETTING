##########IMPORTS##########

import pandas as pd
import datetime as dt
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

##########FUNCTIONS##########

def calculate_predictions():
    
    # Getting 538 data

    tables = pd.read_html(f'https://projects.fivethirtyeight.com/{dt.date.today().year}-nfl-predictions/games/?ex_cid=rrpromo')
    # Instantiating final dataframe of predictions
    df = pd.DataFrame()
    # Iterating through individual game prediction tables from 538 and putting into one dataframe
    for table in tables[:36]:
        if table.shape[0] == 2:
            # Only getting rows/columns/tables I need
            table = table.iloc[:, [1,3]]
            table.columns = ['team', 'win_prob']
            # Appending to list that will be appended to ultimate df
            data_list = []
            for index, row in table.iterrows():
                data_list.append(row.team)
                data_list.append(row.win_prob)
            df = df.append(pd.Series(data_list), ignore_index = True)
    df.columns = ['team_1', 'team_1_prob', 'team_2', 'team_2_prob']

    # Getting odds

    # Instantiating WebDriver
    driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.get('https://www.actionnetwork.com/nfl/odds')
    # Navigating to Moneyline odds
    ml_button = driver.find_element_by_xpath("//*[@id='__next']/div/main/div/div[2]/div/div[1]/div[2]/select")
    select = Select(ml_button)
    select.select_by_visible_text('Moneyline')
    time.sleep(2)
    # Getting data into pandas and formatting
    html = driver.page_source
    tables = pd.read_html(html)
    odds = tables[0]
    odds = odds.iloc[::2]
    odds.reset_index(drop = True, inplace = True)
    # Getting list of team
    teams = list(df.team_1.unique())
    teams.extend(list(df.team_2.unique()))
    teams = list(set(teams))
    # Function to convert odds to probability
    def _calculate_odds(odds):
        if odds<0:
            return (abs(odds)/(abs(odds)+100))*100
        if odds>0:
            return (100/(odds+100))*100
    # Iterating through to get home/away and odds
    odds_df = pd.DataFrame(columns = ['Home_Team', 'Away_Team', 'Home_Odds', 'Away_Odds'])
    for index, row in odds.iterrows():
        # Retreiving home and away teams
        teams_dict = {}
        for team in teams:
            if row.Scheduled.find(team) != -1:
                teams_dict[row.Scheduled.find(team)] = team
        keys = []
        for key in teams_dict.keys():
            keys.append(key)
        if keys[0] > keys[1]:
            home_team = teams_dict[keys[0]]
            away_team = teams_dict[keys[1]]
        else:
            home_team = teams_dict[keys[1]]
            away_team = teams_dict[keys[0]]
        # Retreiving odds
        ml_string = row['Unnamed: 5']
        if len(ml_string) == 8:
            ml_away = ml_string[:4]
            ml_home = ml_string[-4:]
        elif len(ml_string) == 9:
            if (ml_string[4] == '+') | (ml_string[4]=='-'):
                ml_away = ml_string[:4]
                ml_home = ml_string[-5:]
            else:
                ml_away = ml_string[:5]
                ml_home = ml_string[-4:]
        elif len(ml_string) == 10:
                ml_away = ml_string[:5]
                ml_home = ml_string[-5:]
        else:
            continue
        try:
            ml_away = float(ml_away)
        except:
            continue
        try:
            ml_home = float(ml_home)
        except:
            continue
        # Appending to df
        series = pd.Series([home_team, away_team, ml_home, ml_away], index = odds_df.columns)
        odds_df = odds_df.append(series, ignore_index = True)
    # Creating columns converting odds to probability
    odds_df['Home_Prob'] = odds_df.Home_Odds.apply(_calculate_odds)
    odds_df['Away_Prob'] = odds_df.Away_Odds.apply(_calculate_odds)

    # Joining odds to 538 projections and generating bets

    final_df = df.merge(odds_df, )

    return

def calculate_results():
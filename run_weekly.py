##########IMPORTS##########

import pandas as pd
import datetime as dt
import time
import os
import re
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

# Function to convert odds to probability

def _calculate_odds(odds):
    if odds<0:
        return (abs(odds)/(abs(odds)+100))*100
    if odds>0:
        return (100/(odds+100))*100

def _calculate_kc(row, kelly, Home):
    if Home:
        diff = row.Home_Prob_538 - row.Home_Prob_Odds
        if diff<0:
            return 0
        else:
            p = row.Home_Prob_538
            q = 1-p
            ml = row.Home_Odds
            if ml>=0:
                b = (ml/100)
            if ml<0:
                b = (100/abs(ml))
            kc = ((p*b) - q) / b
            if (kc > 0.5) & (kc<0.6):
                return kc/(kelly+2)
            if (kc > 0.6) & (kc<0.7):
                return kc/(kelly+4)
            if kc > 0.7:
                return kc/(kelly+7)
            else:
                return kc/kelly
    if not Home:
        diff = row.Away_Prob_538 - row.Away_Prob_Odds
        if diff<0:
            return 0
        else:
            p = row.Away_Prob_538
            q = 1-p
            ml = row.Away_Odds
            if ml>=0:
                b = (ml/100)
            if ml<0:
                b = (100/abs(ml))
            kc = ((p*b) - q) / b
            if (kc > 0.5) & (kc<0.6):
                return kc/(kelly+2)
            if (kc > 0.6) & (kc<0.7):
                return kc/(kelly+4)
            if kc > 0.7:
                return kc/(kelly+7)
            else:
                return kc/kelly

def _calculate_payoff(row):
    if row.Bet<=0:
        payoff = 0
    else:
        if row.Home_KC>0:
            if row.Home_Odds>0:
                payoff = (row.Home_Odds/100)*row.Bet
            if row.Home_Odds<0:
                payoff = row.Bet/((abs(row.Home_Odds)/100))
        if row.Away_KC>0:
            if row.Away_Odds>0:
                payoff = (row.Away_Odds/100)*row.Bet
            if row.Away_Odds<0:
                payoff = row.Bet/((abs(row.Away_Odds)/100))
    return payoff

def calculate_predictions(capital):
    
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

    final_df = df.merge(odds_df, left_on = 'team_2', right_on = 'Home_Team')
    final_df = final_df[['Home_Team', 'Away_Team', 'Home_Odds', 'Away_Odds', 'Home_Prob', 'Away_Prob', 
                        'team_2_prob', 'team_1_prob']]
    final_df.columns = ['Home_Team', 'Away_Team', 'Home_Odds', 'Away_Odds', 'Home_Prob_Odds', 'Away_Prob_Odds', 
                        'Home_Prob_538', 'Away_Prob_538']
    # Formatting columns for KC
    final_df['Home_Prob_538'] = final_df.Home_Prob_538.str.strip('%')
    final_df['Away_Prob_538'] = final_df.Away_Prob_538.str.strip('%')
    final_df['Home_Prob_538'] = final_df.Home_Prob_538.astype('float') / 100.0
    final_df['Away_Prob_538'] = final_df.Away_Prob_538.astype('float') / 100.0
    final_df['Home_Prob_Odds'] = final_df.Home_Prob_Odds / 100.0
    final_df['Away_Prob_Odds'] = final_df.Away_Prob_Odds / 100.0
    # Creating bets
    final_df['Home_KC'] = final_df.apply(_calculate_kc, axis = 1, kelly = 10, Home = True)
    final_df['Away_KC'] = final_df.apply(_calculate_kc, axis = 1, kelly = 10, Home = False)
    final_df['Bet'] = final_df.apply(lambda x: capital * x.Home_KC if x.Home_KC>0
            else capital * x.Away_KC, axis = 1)

    # Saving

    final_df.to_csv(f'Bets/Bets_{dt.date.today()}.csv')

    return

def calculate_results(week, capital):

    # Getting winners

    #Instantiating stuff used throughout
    winners = []
    team_regex = r'\D+'
    #Iterating through tables and finding winners
    tables = pd.read_html(f'https://www.cbssports.com/nfl/scoreboard/all/2022/regular/{week}/')
    for table in tables:
        if table.columns[0] == tables[0].columns[0]:
            table['Team'] = table['Unnamed: 0'].apply(lambda x: re.findall(team_regex, x)[0])
            table = table[['Team', 'T']]
            table.columns = ['Team', 'Score']
            table['Score'] = table.Score.astype('float')
            if table.iloc[0, 1] > table.iloc[1,1]:
                winners.append(table.iloc[0,0])
            elif table.iloc[0, 1] == table.iloc[1,1]:
                pass
            else:
                winners.append(table.iloc[1,0])
    
    # Determining if bets hit or not
    files = os.listdir('Bets')
    lw_bets = pd.read_csv(f'Bets/{files[-1]}', index_col = 0)
    lw_bets['Payoff'] = lw_bets.apply(_calculate_payoff, axis = 1)
    lw_bets['Won_Bet'] = lw_bets.apply(lambda x: 1 if (x.Home_KC > 0 and x.Home_Team in winners) or 
                                    (x.Away_KC > 0 and x.Away_Team in winners) else
                                    (-1 if ((x.Home_Team not in winners) and (x.Away_Team not in winners)) 
                                        or x.Bet <= 0 else 0), axis = 1)
    # Tracking capital
    lw_bets['Capital_Tracker'] = 0
    for index, row in lw_bets.iterrows():
        if index == 0:
            if row.Won_Bet == 1:
                lw_bets.loc[index, 'Capital_Tracker'] = capital + row.Payoff
            if row.Won_Bet == -1:
                lw_bets.loc[index, 'Capital_Tracker'] = capital
            if row.Won_Bet == 0:
                lw_bets.loc[index, 'Capital_Tracker'] = capital - row.Bet
        else:
            if row.Won_Bet == 1:
                lw_bets.loc[index, 'Capital_Tracker'] = lw_bets.loc[(index-1), 'Capital_Tracker'] + row.Payoff
            if row.Won_Bet == -1:
                lw_bets.loc[index, 'Capital_Tracker'] = lw_bets.loc[(index-1), 'Capital_Tracker']
            if row.Won_Bet == 0:
                lw_bets.loc[index, 'Capital_Tracker'] = lw_bets.loc[(index-1), 'Capital_Tracker'] - row.Bet

    # Saving results

    if week == 1:
        lw_bets.to_csv('Results.csv')
    else:
        results = pd.read_csv('Results.csv', index_col = 0)
        results = results.append(lw_bets)
        results.reset_index(drop = True, inplace = True)
        results.to_csv('Results.csv')
    
    return

##########SCRIPT##########

# Getting some inputs for results tracking function
week = float(input('Sir Hank, what week do we need results from?'))
if week == 1:
    capital = 100000
else:
    tf_results = pd.read_csv('Results.csv', index_col =  0)
    capital = float(tf_results.loc[len(tf_results)-1, 'Capital_Tracker'])
# Results updates and new bets
calculate_results(week = week, capital = capital)
tf_results = pd.read_csv('Results.csv', index_col =  0)
capital = float(tf_results.loc[len(tf_results)-1, 'Capital_Tracker'])
calculate_predictions(capital = capital)

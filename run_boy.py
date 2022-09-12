##########IMPORTS##########

import pandas as pd
import datetime as dt

##########FUNCTIONS##########

def retreive_boy_predictions():
    tables = pd.read_html(f'https://projects.fivethirtyeight.com/{dt.date.today().year}-nfl-predictions/?ex_cid=rrpromo')
    df = tables[0]
    # Getting rid of multi-index & other formatting
    df.columns = df.columns.droplevel(0)
    df = df[['team', 'recordsim. record', 'point diff.', 'make playoffs', 'win division']]
    df.columns = ['team', 'proj_record', 'proj_points_diff', 'prob_playoffs', 'prob_division']
    df.to_csv('BOY_projections.csv')
    
    return df

##########SCRIPT##########

retreive_boy_predictions()
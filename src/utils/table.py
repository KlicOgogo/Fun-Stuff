import pandas as pd

from utils.categories import LESS_TO_WIN_CATEGORIES
from utils.globals import N_RECENT_MATCHUPS


def add_position_column(df):
    position = {index: i + 1 for i, index in enumerate(df.index)}
    df_position = pd.DataFrame(list(position.values()), index=position.keys(), columns=['Pos'])
    result_df = df_position.merge(df, how='inner', left_index=True, right_index=True)
    return result_df


def get_extremums(df, opp_flag):
    hockey_categories = {
        'G', 'A', '+/-', 'PIM', 'FOW', 'ATOI', 'SOG', 'HIT', 'BLK', 'DEF', 'STP', 'PPP', 'SHP', 
        'W', 'GA', 'SV', 'GAA', 'SV%', 'SO'
    }
    basketball_categories = {
        'FG%', 'FT%', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PTS', '3P%', 'DD', 'PF', 'TD', '3P%'
    }
    categories = hockey_categories | basketball_categories
    no_value_cols = {
        'Pos', f'L{N_RECENT_MATCHUPS}%', '%',
        'League', 'TP', 'ER', 'SUM',
        'W  ', 'L', 'D', 'WD', 'LD', 'DD  ',
        'MIN ', 'GP ', 'Diff'
    }
    
    best = {}
    worst = {}
    for col in df.columns:
        if col in no_value_cols | {f'{col} ' for col in categories}:
            best[col], worst[col] = ('', '')
        elif col == 'Team':
            best[col], worst[col] = ('Best', 'Worst')
        elif col in categories | {'MIN', 'GP'}:
            extremums = (df[col].max(), df[col].min())
            best[col], worst[col] = extremums[::-1] if col in LESS_TO_WIN_CATEGORIES else extremums
        else:
            scores_for_sort = []
            power_calc_lambda = lambda x: x[0] + x[2] * 0.5
            for sc in df[col]:
                sc_values = list(map(float, sc.split('-')))
                if len(sc_values) == 3:
                    scores_for_sort.append([power_calc_lambda(sc_values), *[sc_values[i] for i in [0, 2, 1]]])
                else:
                    raise Exception('Unexpected value format.')
            max_val = min(scores_for_sort) if opp_flag else max(scores_for_sort)
            min_val = max(scores_for_sort) if opp_flag else min(scores_for_sort)
            normalizer = lambda x: [x[i] for i in [1, 3, 2]]
            formatter = lambda x: '-'.join(map(lambda num: f'{num:g}', x))
            best[col], worst[col] = formatter(normalizer(max_val)), formatter(normalizer(min_val))      
    return best, worst

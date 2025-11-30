import copy
from operator import itemgetter

import numpy as np
import pandas as pd

from table import style
from table.common import add_position_column


def luck_score(luck, matchups, opp_flag, n_last):
    df_data = copy.deepcopy(luck)
    for team in df_data:
        n_positive = np.sum(np.array(df_data[team]) > 0)
        n_negative = np.sum(np.array(df_data[team]) < 0)

        df_data[team].append(n_positive if opp_flag else n_negative)
        df_data[team].append(n_negative if opp_flag else n_positive)

        df_data[team].append(np.sum(luck[team][-n_last:]))
        df_data[team].append(np.sum(luck[team]))

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    recent_col = f'Last{n_last}'
    cols = [*matchups, '&#128532;', '&#128526;', recent_col, 'SUM']
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=cols)
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    sort_cols = ['&#128532;', '&#128526;', recent_col, 'SUM'] \
        if opp_flag else ['&#128526;', '&#128532;', recent_col, 'SUM']
    sort_indexes = np.lexsort([df[col] * coeff for col, coeff in zip(sort_cols, [1.0, -1.0, 1.0, 1.0])])
    df = df.iloc[sort_indexes]
    df = add_position_column(df)
    styler = df.style.format({c: '{:g}' for c in set(cols) - {'Team'}}).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        map(style.opponent_luck_score if opp_flag else style.value, subset=matchups)
    return styler.to_html()


def top(data, n_top, cols, drop_league_col_flag):
    df_data = sorted(data, key=itemgetter(1), reverse=True)[:n_top]
    df = pd.DataFrame(df_data, index=np.arange(n_top), columns=cols)
    df = add_position_column(df)
    if drop_league_col_flag:
        df.drop('League', axis=1, inplace=True)
    styler = df.style.format({c: '{:g}' for c in set(cols) - {'Team', 'League'}}).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS).hide()
    return styler.to_html()

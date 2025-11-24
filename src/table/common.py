from collections import Counter, defaultdict
import copy
from operator import itemgetter

import numpy as np
import pandas as pd

from table import flag, style
from utils.globals import N_RECENT_MATCHUPS
import utils.table


def h2h(h2h_comparisons):
    h2h_sums = {}
    h2h_powers = {}
    for team in h2h_comparisons:
        team_h2h_sum = sum(h2h_comparisons[team].values(), Counter())
        h2h_sums[team] = [team_h2h_sum[result] for result in ['W', 'L', 'D']]
        h2h_powers[team] = (np.sum(np.array(h2h_sums[team]) * np.array([1.0, 0.0, 0.5])), team_h2h_sum['W'])
    h2h_sums_sorted = sorted(h2h_powers.items(), key=itemgetter(1), reverse=True)
    h2h_order = [team for team, _ in h2h_sums_sorted]

    h2h_data = defaultdict(list)
    for team in h2h_order:
        for opp in h2h_order:
            if team == opp:
                h2h_data[team].append('')
            else:
                comp = h2h_comparisons[team][opp]
                h2h_data[team].append('-'.join(map(str, [comp['W'], comp['L'], comp['D']])))

    df_data = []
    for team in h2h_order:
        team_data = []
        team_data.append(team[0])
        team_data.extend(h2h_data[team])
        team_data.extend(h2h_sums[team])
        team_data.append(np.round(h2h_powers[team][0] / np.sum(h2h_sums[team]), 2))
        df_data.append(team_data)

    df = pd.DataFrame(df_data, columns=['Team', *np.arange(1, len(df_data)+1), 'W  ', 'L', 'D', '%'])
    df = utils.table.add_position_column(df)
    styler = df.style.format({'%': '{:g}'}).set_table_styles(style.STYLES).set_table_attributes(style.ATTRS).hide().\
        map(style.percentage, subset=['%'])
    return styler.to_html()


def places(places_data, matchups, opp_flag, is_overall):
    df_data = copy.deepcopy(places_data)
    for team in df_data:
        n_top = np.sum(flag.top_place(np.array(df_data[team]), df_data))
        n_bottom = np.sum(flag.bottom_place(np.array(df_data[team]), df_data))

        df_data[team].append(n_top if opp_flag else n_bottom)
        df_data[team].append(n_bottom if opp_flag else n_top)

        df_data[team].append(np.sum(places_data[team][-N_RECENT_MATCHUPS:]))
        df_data[team].append(np.sum(places_data[team]))
        
    df_teams = pd.DataFrame(list(map(itemgetter(2, 0) if is_overall else itemgetter(0), df_data.keys())),
                            index=df_data.keys(), columns=['League', 'Team'] if is_overall else ['Team'])
    recent_col = f'Last{N_RECENT_MATCHUPS}'
    cols = [*matchups, '&#128532;', '&#128526;', recent_col, 'SUM']
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=cols)
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    sort_cols = ['&#128526;', '&#128532;', recent_col, 'SUM'] if opp_flag else ['&#128532;', '&#128526;', recent_col, 'SUM']
    sort_indexes = np.lexsort([df[col] * coeff for col, coeff in zip(sort_cols, [1.0, -1.0, 1.0, 1.0])])
    df = df.iloc[sort_indexes]
    df = utils.table.add_position_column(df)
    styler = df.style.format({c: '{:g}' for c in set(cols) - {'Team'}}).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(style.opponent_place if opp_flag else style.place, subset=matchups)
    return styler.to_html()


def scores(scores_data, matchups, opp_flag):
    df_data = copy.deepcopy(scores_data)
    flags = [flag.top_score, flag.half_top_score, flag.half_bottom_score, flag.bottom_score]
    flags = list(reversed(flags)) if opp_flag else flags
    masks = [[] for _ in flags]
    for m in matchups:
        value_row = np.array([df_data[team][m-1] for team in sorted(df_data)])
        for mask_array, flag_func in zip(masks, flags):
            mask_array.append(flag_func(value_row, value_row))
    counts = [np.array(mask_array).sum(axis=0) for mask_array in masks]
    for index, team in enumerate(sorted(df_data)):
        for count_array in counts:
            df_data[team].append(count_array[index])

        df_data[team].append(np.sum(scores_data[team][-N_RECENT_MATCHUPS:]))
        df_data[team].append(np.sum(scores_data[team]))
        
    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    emoji_cols = ['&#128526;', '&#128527;', '&#128532;', '&#128557;']
    recent_col = f'Last{N_RECENT_MATCHUPS}'
    cols = [*matchups, *emoji_cols, recent_col, 'SUM']
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=cols)
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    sort_cols = [*emoji_cols, recent_col, 'SUM'] if opp_flag else [*reversed(emoji_cols), recent_col, 'SUM']
    sort_indexes = np.lexsort([df[col] * coeff for col, coeff in zip(sort_cols, [1.0, 1.0, -1.0, -1.0, -1.0, -1.0])])
    df = df.iloc[sort_indexes]
    df = utils.table.add_position_column(df)
    styler = df.style.format({c: '{:g}' for c in set(cols) - {'Team'}}).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(style.opponent_score if opp_flag else style.score, subset=matchups)
    return styler.to_html()

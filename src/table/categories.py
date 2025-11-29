from collections import Counter
import copy
from operator import itemgetter

import numpy as np
import pandas as pd

from table import style
from table.common import add_position_column


_hockey_categories = {
        'G', 'A', '+/-', 'PIM', 'FOW', 'ATOI', 'SOG', 'HIT', 'BLK', 'DEF', 'STP', 'PPP', 'SHP', 
        'W', 'GA', 'SV', 'GAA', 'SV%', 'SO'
    }
_basketball_categories = {
    'FG%', 'FT%', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PTS', '3P%', 'DD', 'PF', 'TD', '3P%'
}
_categories = _hockey_categories | _basketball_categories
_no_value_cols = {
    'Pos', '%',
    'League', 'TP', 'ER', 'SUM',
    'W  ', 'L', 'D', 'WD', 'LD', 'DD  ',
    'MIN ', 'GP ', 'Diff', 'Team',
}


def _get_extremums(df, opp_flag, n_last, less_to_win_categories):
    best = {}
    worst = {}
    for col in df.columns:
        if col in _no_value_cols | {f'{col} ' for col in _categories} | {f'L{n_last}%'}:
            best[col], worst[col] = ('', '')
        elif col in _categories | {'MIN', 'GP'}:
            extremums = (df[col].max(), df[col].min())
            best[col], worst[col] = extremums[::-1] if col in less_to_win_categories else extremums
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


def comparisons(comparisons_data, matchups, opp_flag, n_last, less_to_win_categories):
    df_data = copy.deepcopy(comparisons_data)
    for team in df_data:
        team_stats = [np.array(list(map(int, score.split('-')))) for score in df_data[team]]
        comparisons_sum = np.vstack(team_stats).sum(axis=0)
        df_data[team].extend(comparisons_sum)
        team_power = np.sum(comparisons_sum * np.array([1.0, 0.0, 0.5]))
        team_power_norm = team_power / np.sum(comparisons_sum)

        recent_comparisons_sum = np.vstack(team_stats[-n_last:]).sum(axis=0)
        recent_team_power = np.sum(recent_comparisons_sum * np.array([1.0, 0.0, 0.5]))
        recent_team_power_norm = recent_team_power / np.sum(recent_comparisons_sum)
        df_data[team].append(np.round(recent_team_power_norm, 2))

        df_data[team].append(np.round(team_power_norm, 2))
    
    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    perc_cols = [f'L{n_last}%', '%']
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=[*matchups, 'W  ', 'L', 'D', *perc_cols])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    sort_sign = 1 if opp_flag else -1
    df = df.iloc[np.lexsort((sort_sign * df['W  '], sort_sign * (df['W  '] + df['D'] * 0.5)))]
    df = add_position_column(df)
    best, worst = _get_extremums(df, opp_flag, n_last, less_to_win_categories)
    styler = df.style.format('{:g}', subset=pd.IndexSlice[list(df_data.keys()), perc_cols]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(lambda s: style.extremum(s, best[s.name], worst[s.name]), subset=matchups).\
        map(style.percentage, subset=pd.IndexSlice[list(df_data.keys()), perc_cols])
    return styler.to_html()


def expected_each_category_stats(data, expected_data, matchup, n_last, less_to_win_categories):
    df_data = copy.deepcopy(expected_data)
    for team in df_data:
        team_stats_array = np.vstack(df_data[team])
        df_data[team].append(team_stats_array.sum(axis=0))
        df_data[team].append(data[team])
        df_data[team].extend(map(lambda x: np.round(x, 1), df_data[team][-1] - df_data[team][-2]))
        for i in range(len(df_data[team]) - 3):
            df_data[team][i] = '-'.join(map(lambda x: f'{np.round(x, 1):g}', df_data[team][i][:3]))
        df_data[team].append(df_data[team][-3] + 0.5 * df_data[team][-1])

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    matchups = np.arange(1, matchup + 1)
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                      columns=[*matchups, 'Total', 'Real', 'WD', 'LD', 'DD  ', 'Diff'])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['WD'], -df['Diff']))]
    df = add_position_column(df)
    best, worst = _get_extremums(df, False, n_last, less_to_win_categories)
    extremum_lambda = lambda s: style.extremum(s, best[s.name], worst[s.name])
    styler = df.style.format('{:g}', subset=pd.IndexSlice[list(df_data.keys()), ['DD  ', 'WD', 'LD', 'Diff']]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        map(style.value, subset=pd.IndexSlice[list(df_data.keys()), ['Diff']]).\
        apply(extremum_lambda, subset=pd.IndexSlice[df.index, [*matchups, 'Total', 'Real']])
    return styler.to_html()


def expected_win_stats(data, expected_data, matchups):
    df_data = copy.deepcopy(expected_data)
    res_order = ['W', 'L', 'D']
    for team in df_data:
        expected_record = Counter(df_data[team])
        expected_record_str = '-'.join(map(lambda num: f'{num:g}', [expected_record[res] for res in res_order]))
        df_data[team].append(expected_record_str)
        record_str = '-'.join(map(lambda num: f'{num:g}', [data[team][res] for res in res_order]))
        df_data[team].append(record_str)
        df_data[team].extend([data[team][res] - expected_record[res] for res in res_order])
        df_data[team].append(df_data[team][-3] + 0.5 * df_data[team][-1])
    
    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                      columns=[*matchups, 'Total', 'Real', 'WD', 'LD', 'DD  ', 'Diff'])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['WD'], -df['Diff']))]
    df = add_position_column(df)
    styler = df.style.format('{:g}', subset=pd.IndexSlice[list(df_data.keys()), ['Diff']]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        map(style.pair_result, subset=matchups).\
        map(style.value, subset=pd.IndexSlice[list(df_data.keys()), ['Diff']])
    return styler.to_html()


def matchup(categories, stats_data, matchup_scores, plays_data, places_data, comparisons, expected_data, n_last, less_to_win_categories):
    is_overall = len(set(map(itemgetter(2), stats_data.keys()))) > 1
    df = pd.DataFrame(list(map(itemgetter(2, 0) if is_overall else itemgetter(0), stats_data.keys())),
                      index=stats_data.keys(), columns=['League', 'Team'] if is_overall else ['Team'])
    df_stats = pd.DataFrame(list(stats_data.values()), index=stats_data.keys(), columns=categories)
    if plays_data:
        data = plays_data[1]
        df_data = pd.DataFrame(list(data.values()), index=data.keys(), columns=[plays_data[0]])
        df = df.merge(df_data, how='outer', left_index=True, right_index=True)
    df = df.merge(df_stats, how='outer', left_index=True, right_index=True)
    matchup_scores_dict = {}
    for s in matchup_scores:
        matchup_scores_dict.update(s)
    df_score = pd.DataFrame(list(matchup_scores_dict.values()), index=matchup_scores_dict.keys(), columns=['Score'])
    df = df.merge(df_score, how='outer', left_index=True, right_index=True)

    is_each_category = False
    er_data = {}
    for team in expected_data:
        if len(expected_data[team]) > 1:
            er_data[team] = '-'.join(map(lambda x: f'{np.round(x, 1):g}', expected_data[team]))
            is_each_category = True
        else:
            er_data[team] = expected_data[team]
    er_df_col = ['ExpScore' if is_each_category else 'ER']
    df_er = pd.DataFrame(list(er_data.values()), index=er_data.keys(), columns=er_df_col)
    df = df.merge(df_er, how='outer', left_index=True, right_index=True)
    calc_power_lambda = lambda x: x[0] + x[2] * 0.5
    n_opponents = len(comparisons) - 1
    team_power = {team: np.round(calc_power_lambda(comparisons[team]) / n_opponents, 2) for team in comparisons}
    df_tp = pd.DataFrame(list(team_power.values()), index=team_power.keys(), columns=['TP'])
    df = df.merge(df_tp, how='outer', left_index=True, right_index=True)
    
    if plays_data:
        data = plays_data[2]
        df_data = pd.DataFrame(list(data.values()), index=data.keys(), columns=[f'{plays_data[0]} '])
        df = df.merge(df_data, how='outer', left_index=True, right_index=True)
    for team in places_data:
        places_data[team].append(np.sum(places_data[team]))
    places_cols = [f'{col} ' for col in categories]
    df_places = pd.DataFrame(list(places_data.values()), index=places_data.keys(), columns=places_cols + ['SUM'])
    df = df.merge(df_places, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['PTS'], df['SUM']))]
    df = add_position_column(df)

    best, worst = _get_extremums(df, False, n_last, less_to_win_categories)
    extremum_cols = categories + ['Score']
    if is_each_category:
        extremum_cols.append('ExpScore')
    if plays_data:
        extremum_cols.append(plays_data[0])

    num_cols = set(df.columns) - {'Team', 'League', 'Score', 'ER', 'ExpScore', 'ATOI'}
    cols_minus = {*categories, plays_data[0]} if plays_data else set(categories)
    extremum_lambda = lambda s: style.extremum(s, best[s.name], worst[s.name])
    styler = df.style.format('{:g}', subset=pd.IndexSlice[df_stats.index, list(num_cols - cols_minus)]).\
        format('{:g}', subset=pd.IndexSlice[df.index, list(set(categories) - {'ATOI'})]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(extremum_lambda, subset=pd.IndexSlice[df.index, extremum_cols]).\
        apply(style.place, subset=pd.IndexSlice[df_stats.index, places_cols]).\
        map(style.percentage, subset=pd.IndexSlice[df_stats.index, ['TP']])
    if not is_each_category:
        styler = styler.map(style.pair_result, subset=pd.IndexSlice[df_stats.index, ['ER']])
    if plays_data:
        styler = styler.apply(style.place, subset=pd.IndexSlice[df_stats.index, [f'{plays_data[0]} ']])
    return styler.to_html()

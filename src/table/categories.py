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


def _get_extremums(df, less_to_win_categories, is_opponent, n_last=None):
    best = {}
    worst = {}
    for col in df.columns:
        if col in _no_value_cols | {f'{col} ' for col in _categories} | ({f'L{n_last}%'} if n_last else set()):
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
            max_val = min(scores_for_sort) if is_opponent else max(scores_for_sort)
            min_val = max(scores_for_sort) if is_opponent else min(scores_for_sort)
            normalizer = lambda x: [x[i] for i in [1, 3, 2]]
            formatter = lambda x: '-'.join(map(lambda num: f'{num:g}', x))
            best[col], worst[col] = formatter(normalizer(max_val)), formatter(normalizer(min_val))
    return best, worst


def _matchup_metrics(metrics):
    matchup_scores_dict = {}
    for s in metrics['Score']:
        matchup_scores_dict.update(s)
    df = pd.DataFrame(list(matchup_scores_dict.values()), index=matchup_scores_dict.keys(), columns=['Score'])

    expected_scores = metrics.get('ExpScore', None)
    if expected_scores is not None:
        exp_score_df_data = {}
        for team in expected_scores:
            exp_score_df_data[team] = '-'.join(map(lambda x: f'{x:.1f}', expected_scores[team]))
        df_exp_score = pd.DataFrame(list(exp_score_df_data.values()), index=exp_score_df_data.keys(),
                                    columns=['ExpScore'])
        df = df.merge(df_exp_score, how='outer', left_index=True, right_index=True)

    expected_results = metrics.get('ER', None)
    if expected_results is not None:
        df_er = pd.DataFrame(list(expected_results.values()), index=expected_results.keys(), columns=['ER'])
        df = df.merge(df_er, how='outer', left_index=True, right_index=True)

    calc_power_lambda = lambda x: x[0] + x[2] * 0.5
    comparisons = metrics['TP']
    n_opponents = len(comparisons) - 1
    team_power = {team: np.round(calc_power_lambda(comparisons[team]) / n_opponents, 2) for team in comparisons}
    df_tp = pd.DataFrame(list(team_power.values()), index=team_power.keys(), columns=['TP'])
    df = df.merge(df_tp, how='outer', left_index=True, right_index=True)

    return df


def pairwise_comparisons(comparisons_data, matchups, is_opponent, n_last, less_to_win_categories):
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
    sort_sign = 1 if is_opponent else -1
    df = df.iloc[np.lexsort((sort_sign * df['W  '], sort_sign * (df['W  '] + df['D'] * 0.5)))]
    df = add_position_column(df)
    best, worst = _get_extremums(df, less_to_win_categories, is_opponent, n_last)
    styler = df.style.format('{:g}', subset=pd.IndexSlice[list(df_data.keys()), perc_cols]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(lambda s: style.extremum(s, best[s.name], worst[s.name]), subset=matchups).\
        map(style.percentage, subset=pd.IndexSlice[list(df_data.keys()), perc_cols])
    return styler.to_html()


def expected_category_stats(data, expected_data, matchups, less_to_win_categories):
    df_data = copy.deepcopy(expected_data)
    for team in df_data:
        team_stats_array = np.vstack(df_data[team])
        df_data[team].append(team_stats_array.sum(axis=0))
        df_data[team].append(data[team])
        df_data[team].extend(map(lambda x: np.round(x, 1), df_data[team][-1] - df_data[team][-2]))
        for i in range(len(df_data[team]) - 3):
            df_data[team][i] = '-'.join(map(lambda x: f'{x:.1f}', df_data[team][i][:3]))
        df_data[team].append(df_data[team][-3] + 0.5 * df_data[team][-1])

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                      columns=[*matchups, 'Total', 'Real', 'WD', 'LD', 'DD  ', 'Diff'])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['WD'], -df['Diff']))]
    df = add_position_column(df)
    best, worst = _get_extremums(df, less_to_win_categories, is_opponent=False)
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


def matchup(stats_with_plays, places_with_plays, places_sum, categories_with_plays, less_to_win_categories, metrics):
    is_overall = len(set(map(itemgetter(2), stats_with_plays.keys()))) > 1
    df = pd.DataFrame(list(map(itemgetter(2, 0) if is_overall else itemgetter(0), stats_with_plays.keys())),
                      index=stats_with_plays.keys(), columns=['League', 'Team'] if is_overall else ['Team'])

    df_stats = pd.DataFrame(list(stats_with_plays.values()), index=stats_with_plays.keys(),
                            columns=categories_with_plays)
    df = df.merge(df_stats, how='outer', left_index=True, right_index=True)

    df_metrics = _matchup_metrics(metrics)
    df = df.merge(df_metrics, how='outer', left_index=True, right_index=True)

    places_cols = [f'{col} ' for col in categories_with_plays]
    df_places = pd.DataFrame(list(places_with_plays.values()), index=places_with_plays.keys(), columns=places_cols)
    df = df.merge(df_places, how='outer', left_index=True, right_index=True)
    df_places_sum = pd.DataFrame(list(places_sum.values()), index=places_sum.keys(), columns=['SUM'])
    df = df.merge(df_places_sum, how='outer', left_index=True, right_index=True)

    df = df.iloc[np.lexsort((-df['PTS'], df['SUM']))]
    df = add_position_column(df)

    best, worst = _get_extremums(df, less_to_win_categories, is_opponent=False)
    extremum_cols = categories_with_plays + ['Score']
    if 'ExpScore' in metrics:
        extremum_cols.append('ExpScore')

    num_cols = list(set(df.columns) - {'Team', 'League', 'Score', 'ER', 'ExpScore', 'ATOI'})
    extremum_lambda = lambda s: style.extremum(s, best[s.name], worst[s.name])
    styler = df.style.format('{:g}', subset=pd.IndexSlice[df.index, num_cols]).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(extremum_lambda, subset=pd.IndexSlice[df.index, extremum_cols]).\
        apply(style.place, subset=pd.IndexSlice[df_stats.index, places_cols]).\
        map(style.percentage, subset=pd.IndexSlice[df_stats.index, ['TP']])
    if 'ER' in metrics:
        styler = styler.map(style.pair_result, subset=pd.IndexSlice[df_stats.index, ['ER']])
    return styler.to_html()

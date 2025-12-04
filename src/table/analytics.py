from collections import Counter, defaultdict
from operator import itemgetter

import numpy as np
import pandas as pd

from table import common, style


def category_power(places_by_categories, categories, n_last=None):
    df_data = defaultdict(list)
    slice_left = 0 if n_last is None else -n_last
    for category in places_by_categories:
        for team in places_by_categories[category]:
            df_data[team].append(np.mean(places_by_categories[category][team][slice_left:]))

    n_ranks = 5
    n_teams = len(df_data)
    ranges = [(i * n_teams / n_ranks, (i + 1) * n_teams / n_ranks) for i in range(n_ranks)]
    for team in df_data:
        team_row = np.array(df_data[team])
        for rng_left, rng_right in ranges:
            df_data[team].append(np.logical_and(team_row > rng_left, team_row <= rng_right).sum())

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                      columns=categories + ['&#128526;', '&#128527;', '&#128556;', '&#128532;', '&#128557;'])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['&#128532;'], -df['&#128556;'], -df['&#128527;'], -df['&#128526;']))]
    df = common.add_position_column(df)
    styler = df.style.format('{:g}', subset=categories).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(style.category_power, subset=categories)
    return styler.to_html()


def category_rankings(places_by_categories, categories):
    category_powers = defaultdict(list)
    for category in places_by_categories:
        for team in places_by_categories[category]:
            category_powers[team].append((np.mean(places_by_categories[category][team]), category))

    df_data = {}
    for team in category_powers:
        team_powers_sorted = sorted(category_powers[team])
        team_data = list(map(itemgetter(1), team_powers_sorted))
        df_data[team] = team_data

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=np.arange(1, len(categories) + 1))
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((df['Team'],))]
    styler = df.style.set_table_styles(style.STYLES).set_table_attributes(style.ATTRS).hide()
    return styler.to_html()


def h2h_category_record(places_by_categories, categories, my_team_key, n_last):
    df_data = defaultdict(list)
    h2h_records = defaultdict(list)
    recent_h2h_records = defaultdict(list)
    for category in places_by_categories:
        my_team_places = np.array(places_by_categories[category][my_team_key])
        recent_my_team_places = np.array(places_by_categories[category][my_team_key][-n_last:])
        for team in places_by_categories[category]:
            if team == my_team_key:
                continue

            opponent_places = np.array(places_by_categories[category][team])
            wins = (my_team_places < opponent_places).sum()
            losses = (my_team_places > opponent_places).sum()
            draws = (my_team_places == opponent_places).sum()
            
            df_data[team].append(f'{wins}-{losses}-{draws}')
            h2h_records[team].append([wins, losses, draws])

            recent_opponent_places = np.array(places_by_categories[category][team][-n_last:])
            recent_wins = (recent_my_team_places < recent_opponent_places).sum()
            recent_losses = (recent_my_team_places > recent_opponent_places).sum()
            recent_draws = (recent_my_team_places == recent_opponent_places).sum()
            recent_h2h_records[team].append([recent_wins, recent_losses, recent_draws])

    for team in h2h_records:
        team_summary = np.sum(h2h_records[team], axis=0)
        team_recent_summary = np.sum(recent_h2h_records[team], axis=0)
        df_data[team].extend(team_summary)
        team_power = np.sum(team_summary * np.array([1.0, 0.0, 0.5]))
        team_recent_power = np.sum(team_recent_summary * np.array([1.0, 0.0, 0.5]))
        df_data[team].append(np.round(team_recent_power / np.sum(team_recent_summary), 2))
        df_data[team].append(np.round(team_power / np.sum(team_summary), 2))

    percentage_cols = [f'L{n_last}%', '%']
    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df_stats = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                            columns=[*categories, 'W  ', 'L', 'D', *percentage_cols])
    df = df_teams.merge(df_stats, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['W  '], -df[f'L{n_last}%'], -df['%']))]
    df = common.add_position_column(df)
    styler = df.style.format('{:g}', subset=percentage_cols).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        map(style.percentage, subset=percentage_cols)
    return styler.to_html()


def power_predictions(places_by_categories, my_team_key, matchups):
    df_data = defaultdict(list)
    sum_stats = defaultdict(list)
    
    for m in matchups:
        matchup_team_data = defaultdict(list)
        for category in places_by_categories:
            for team in places_by_categories[category]:
                matchup_team_data[team].append(np.mean(places_by_categories[category][team][:m]))
        
        my_team_places = np.array(matchup_team_data[my_team_key])
        for team in matchup_team_data:
            if team == my_team_key:
                continue
            opponent_places = np.array(matchup_team_data[team])
            wins = (my_team_places < opponent_places).sum()
            losses = (my_team_places > opponent_places).sum()
            draws = (my_team_places == opponent_places).sum()
            
            df_data[team].append(f'{wins}-{losses}-{draws}')
            sum_stats[team].append([wins, losses, draws])

    for team in sum_stats:
        team_summary = np.sum(sum_stats[team], axis=0)
        df_data[team].extend(team_summary)
        team_power = np.sum(team_summary * np.array([1.0, 0.0, 0.5]))
        df_data[team].append(np.round(team_power / np.sum(team_summary), 2))

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df_stats = pd.DataFrame(list(df_data.values()), index=df_data.keys(), columns=[*matchups, 'W  ', 'L', 'D', '%'])
    df = df_teams.merge(df_stats, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['W  '], -df['%']))]
    df = common.add_position_column(df)
    styler = df.style.format({'%': '{:g}'}).set_table_styles(style.STYLES).set_table_attributes(style.ATTRS).hide().\
        map(style.percentage, subset=['%'])
    return styler.to_html()


def power_predictions_h2h(places_by_categories):
    category_powers = defaultdict(list)
    for category in places_by_categories:
        for team in places_by_categories[category]:
            category_powers[team].append(np.mean(places_by_categories[category][team]))
    
    comparisons_h2h = defaultdict(lambda: defaultdict(Counter))
    for team in category_powers:
        team_places = np.array(category_powers[team])
        for opp in category_powers:
            if team == opp:
                continue
            opponent_places = np.array(category_powers[opp])
            comparisons_h2h[team][opp]['W'] = (team_places < opponent_places).sum()
            comparisons_h2h[team][opp]['L'] = (team_places > opponent_places).sum()
            comparisons_h2h[team][opp]['D'] = (team_places == opponent_places).sum()
    return common.h2h(comparisons_h2h)


def category_win_stats(win_stats, categories, n_last=None):
    df_data = defaultdict(list)
    slice_left = 0 if n_last is None else -n_last
    for category in win_stats:
        for team in win_stats[category]:
            df_data[team].append(np.mean(win_stats[category][team][slice_left:]))

    n_ranks = 5
    ranges = [(-0.00001, 1 / n_ranks)] + [(i / n_ranks, (i + 1) / n_ranks) for i in range(1, n_ranks)]
    for team in df_data:
        team_row = np.array(df_data[team])
        for rng_left, rng_right in reversed(ranges):
            df_data[team].append(np.logical_and(team_row > rng_left, team_row <= rng_right).sum())

    df_teams = pd.DataFrame(list(map(itemgetter(0), df_data.keys())), index=df_data.keys(), columns=['Team'])
    df = pd.DataFrame(list(df_data.values()), index=df_data.keys(),
                      columns=categories + ['&#128526;', '&#128527;', '&#128556;', '&#128532;', '&#128557;'])
    df = df_teams.merge(df, how='outer', left_index=True, right_index=True)
    df = df.iloc[np.lexsort((-df['&#128532;'], -df['&#128556;'], -df['&#128527;'], -df['&#128526;']))]
    df = common.add_position_column(df)
    styler = df.style.format('{:g}', subset=categories).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide().\
        apply(style.each_category_win_stat, subset=categories)
    return styler.to_html()

from collections import defaultdict, Counter
import itertools

import numpy as np

import table.analytics
import table.categories
import table.common
import utils.categories
import utils.common
import utils.data


_less_win_categories = ['TO', 'GAA', 'GA', 'PF']
_plays_cols = {'basketball': 'MIN', 'hockey': 'GP'}
_plays_getters = {'basketball': utils.data.minutes, 'hockey': utils.data.player_games}
_plays_names = {'basketball': 'minutes', 'hockey': 'games'}


def _category_places_tables(categories, category_places, matchups, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    category_names = global_resources['category_names']

    tables = []
    for category in categories:
        name = category_names[category]
        places = category_places[category]
        tables.append([
            titles['category_places'].format(name), descriptions['category_places'].format(name),
            table.common.places(places, matchups, False, False, n_last)])
    return tables


def _each_team_tables(team_keys, categories, category_places, matchups, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    tables = []
    for team_key in team_keys:
        team_name, _, _, _ = team_key
        tables.append([
            titles['team_category_record'].format(team_name), descriptions['team_category_record'],
            table.analytics.h2h_category_record(category_places, categories, team_key, n_last)])
        tables.append([
            titles['result_expectation'].format(team_name), descriptions['result_expectation'],
            table.analytics.power_predictions(category_places, team_key, matchups)])
    return tables


def _analytics_tables(group_settings, matchup, scoreboards, global_resources):
    leagues = group_settings['leagues'].split(',')
    is_analytics_enabled = map(int, group_settings['is_analytics_enabled'].split(','))
    enabled_analytics_leagues = [league for is_enabled, league in zip(is_analytics_enabled, leagues) if is_enabled]
    sports = group_settings['sports']

    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    analytics_tables = []
    matchups = np.arange(1, matchup + 1)
    for league in enabled_analytics_leagues:
        _, team_names, category_pairs, league_name = scoreboards[league]
        categories, category_places, category_win_stats = utils.categories.get_each_category_stats(
            matchup, category_pairs, _less_win_categories)

        tables = []
        tables.append([
            titles['category_win_stats'], descriptions['category_win_stats'],
            table.analytics.category_win_stats(category_win_stats, categories)])
        tables.append([
            titles['recent_category_win_stats'].format(n_last),
            descriptions['recent_category_win_stats'].format(n_last),
            table.analytics.category_win_stats(category_win_stats, categories, n_last)
        ])
        tables.append([
            titles['category_power'], descriptions['category_power'],
            table.analytics.category_power(category_places, categories)])
        tables.append([
            titles['recent_category_power'].format(n_last), descriptions['recent_category_power'].format(n_last),
            table.analytics.category_power(category_places, categories, n_last)
        ])
        tables.append([
            titles['category_rankings'], descriptions['category_rankings'],
            table.analytics.category_rankings(category_places, categories)])
        tables.append([
            titles['result_expectation_h2h'], descriptions['result_expectation_h2h'],
            table.analytics.power_predictions_h2h(category_places)])

        category_places_tables = _category_places_tables(categories, category_places, matchups, global_resources)
        team_keys = [(team_name, team_id, league_name, league) for team_id, team_name in sorted(team_names.items())]
        each_team_tables = _each_team_tables(team_keys, categories, category_places, matchups, global_resources)

        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        league_tables = tables + category_places_tables + each_team_tables
        analytics_tables.append([league_name, league_link, league_tables])
    return analytics_tables


def _matchup_table(league, group_settings, matchup, scoreboards, league_box_scores):
    is_each_category = group_settings['is_each_category']
    sports = group_settings['sports']
    tiebreaker = group_settings['tiebreaker']

    scores, _, category_pairs, _ = scoreboards[league]
    matchup_pairs, categories = category_pairs[matchup - 1]
    stats = utils.categories.get_stats(matchup_pairs)

    places_data = utils.categories.get_places_data(stats, categories, _less_win_categories)
    places_sum = utils.categories.get_places_sum(matchup_pairs, categories, _less_win_categories)
    plays = None if league_box_scores is None else _plays_getters[sports](league_box_scores[matchup - 1])
    plays_places = None if plays is None else utils.common.get_places(plays, reverse=True)
    stats_with_plays = utils.categories.join_stats_and_plays(stats, plays)
    places_with_plays = utils.categories.join_stats_and_plays(places_data, plays_places)
    plays_columns = [] if plays is None else [_plays_cols[sports]]
    categories_with_plays = plays_columns + categories

    matchup_expected_score = utils.categories.get_expected_score(stats, categories, _less_win_categories)
    matchup_tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
        stats, categories, _less_win_categories, tiebreaker)
    opponent_dict = utils.common.get_opponent_dict(matchup_pairs)
    matchup_expected_result = utils.categories.get_expected_result(
        matchup_expected_score, matchup_tiebreaker_stats, opponent_dict)
    matchup_expectations = matchup_expected_score if is_each_category else matchup_expected_result
    expectations_column_name = 'ExpScore' if is_each_category else 'ER'
    comparisons = utils.categories.get_comparison_stats(stats, categories, _less_win_categories, tiebreaker)
    metrics = {
        'Score': scores[matchup - 1],
        expectations_column_name: matchup_expectations,
        'TP': comparisons,
    }

    return table.categories.matchup(
        stats_with_plays, places_with_plays, places_sum, categories_with_plays, _less_win_categories, metrics)


def _overall_stats(group_settings, matchup, scoreboards, box_scores):
    leagues = group_settings['leagues'].split(',')
    sports = group_settings['sports']
    overall_plays = None if box_scores is None else {}
    overall_scores = []
    overall_stats_pairs = [[] for _ in range(matchup)]
    categories = None
    for league in leagues:
        scores, _, category_pairs, _ = scoreboards[league]
        matchup_scores = scores[matchup - 1]
        overall_scores.extend(matchup_scores)
        for m in range(matchup):
            stats_pairs, categories = category_pairs[m]
            overall_stats_pairs[m].extend(stats_pairs)
        plays = None if box_scores is None else _plays_getters[sports](box_scores[league][matchup - 1])
        overall_plays = overall_plays if plays is None else overall_plays | plays

    return {
        'categories': categories,
        'plays': overall_plays,
        'stats_pairs': overall_stats_pairs,
        'scores': overall_scores,
    }


def _overall_tables(group_settings, matchup, overall_stats, global_resources):
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    tiebreaker = group_settings['tiebreaker']
    categories = overall_stats['categories']
    plays = overall_stats['plays']
    stats_pairs = overall_stats['stats_pairs']

    stats = utils.categories.get_stats(stats_pairs[matchup - 1])
    stats_with_plays = utils.categories.join_stats_and_plays(stats, plays)

    places_data = utils.categories.get_places_data(stats, categories, _less_win_categories)
    places_sum = utils.categories.get_places_sum(stats_pairs[matchup - 1], categories, _less_win_categories)
    plays_places = None if plays is None else utils.common.get_places(plays, reverse=True)
    places_with_plays = utils.categories.join_stats_and_plays(places_data, plays_places)
    plays_columns = [] if plays is None else [_plays_cols[group_settings['sports']]]
    categories_with_plays = plays_columns + categories

    expected_score = utils.categories.get_expected_score(stats, categories, _less_win_categories)
    tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
        stats, categories, _less_win_categories, tiebreaker)
    opponent_dict = utils.common.get_opponent_dict(stats_pairs[matchup - 1])
    expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opponent_dict)
    expectations = expected_score if group_settings['is_each_category'] else expected_result
    expectations_column_name = 'ExpScore' if group_settings['is_each_category'] else 'ER'
    comparisons = utils.categories.get_comparison_stats(stats, categories, _less_win_categories, tiebreaker)
    metrics = {
        'Score': overall_stats['scores'],
        expectations_column_name: expectations,
        'TP': comparisons,
    }
    overall_tables = []
    overall_tables.append([
        titles['matchup_overall'], descriptions['matchup_overall'],
        table.categories.matchup(
            stats_with_plays, places_with_plays, places_sum, categories_with_plays, _less_win_categories, metrics)])

    all_leagues_places = defaultdict(list)
    for m in range(matchup):
        matchup_places_sum = utils.categories.get_places_sum(stats_pairs[m], categories, _less_win_categories)
        places_sum_places = utils.common.get_places(matchup_places_sum, False)
        for team in places_sum_places:
            all_leagues_places[team].append(places_sum_places[team])

    n_last = global_resources['config']['n_last_matchups']
    overall_tables.append([
        titles['places_overall'], descriptions['places_overall'],
        table.common.places(all_leagues_places, np.arange(1, matchup + 1), False, True, n_last)
    ])
    return overall_tables


def _plays_tables(sports, matchups, league_box_scores, global_resources):
    if league_box_scores is None:
        return []

    plays = defaultdict(list)
    plays_places = defaultdict(list)
    for matchup in matchups:
        matchup_box_scores_data = league_box_scores[matchup - 1]
        plays_matchup = _plays_getters[sports](matchup_box_scores_data)
        if not plays_matchup:
            raise Exception('Matchup plays for categories not found.')

        for team, value in plays_matchup.items():
            plays[team].append(value)
        matchup_places = utils.common.get_places(plays_matchup, reverse=True)
        for team, value in matchup_places.items():
            plays_places[team].append(value)

    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    table_key = _plays_names[sports]
    plays_tables = [
        [
            titles[table_key], descriptions[table_key],
            table.common.scores(plays, matchups, False, n_last)
        ],
        [
            titles[f'{table_key}_places'], descriptions[f'{table_key}_places'],
            table.common.places(plays_places, matchups, False, False, n_last)
        ],
    ]
    return plays_tables


def _cumulative_stats(matchup, scores, category_pairs, tiebreaker):
    cumulative_stats = {
        'places': defaultdict(list),
        'opponent_places': defaultdict(list),
        'comparisons': defaultdict(list),
        'opponent_comparisons': defaultdict(list),
        'expected_category_record': defaultdict(list),
        'win_record': defaultdict(Counter),
        'expected_win_record': defaultdict(list),
        'comparisons_h2h': defaultdict(lambda: defaultdict(Counter)),
    }
    for m in np.arange(1, matchup + 1):
        stats_pairs, categories = category_pairs[m-1]
        opponent_dict = utils.common.get_opponent_dict(stats_pairs)
        matchup_places_sum = utils.categories.get_places_sum(stats_pairs, categories, _less_win_categories)
        matchup_places = utils.common.get_places(matchup_places_sum, False)
        for team in matchup_places:
            cumulative_stats['places'][team].append(matchup_places[team])
            cumulative_stats['opponent_places'][team].append(matchup_places[opponent_dict[team]])

        stats = utils.categories.get_stats(stats_pairs)
        comparison_stats = utils.categories.get_comparison_stats(stats, categories, _less_win_categories, tiebreaker)
        for team in comparison_stats:
            matchup_comparisons = '-'.join(map(str, comparison_stats[team]))
            cumulative_stats['comparisons'][team].append(matchup_comparisons)
            opponent_matchup_comparisons = '-'.join(map(str, comparison_stats[opponent_dict[team]]))
            cumulative_stats['opponent_comparisons'][team].append(opponent_matchup_comparisons)

        for team in opponent_dict:
            opponent = opponent_dict[team]
            team_result, _ = utils.categories.get_pair_result(
                stats[team], stats[opponent], categories, _less_win_categories, tiebreaker)
            cumulative_stats['win_record'][team][team_result] += 1

        expected_score = utils.categories.get_expected_score(stats, categories, _less_win_categories)
        tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
            stats, categories, _less_win_categories, tiebreaker)
        expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opponent_dict)
        for team in expected_score:
            cumulative_stats['expected_category_record'][team].append(expected_score[team])
            cumulative_stats['expected_win_record'][team].append(expected_result[team])

        for team, opponent in itertools.combinations(stats.keys(), 2):
            team_result, opponent_result = utils.categories.get_pair_result(
                stats[team], stats[opponent], categories, _less_win_categories, tiebreaker)
            cumulative_stats['comparisons_h2h'][team][opponent][team_result] += 1
            cumulative_stats['comparisons_h2h'][opponent][team][opponent_result] += 1

    cumulative_stats['category_record'] = utils.categories.calculate_category_record(scores)
    return cumulative_stats


def _cumulative_tables(cumulative_stats, matchups, global_resources, is_each_category):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    tables = []
    places = cumulative_stats['places']
    tables.append([
        titles['places'], descriptions['places'],
        table.common.places(places, matchups, False, False, n_last)])
    opponent_places = cumulative_stats['opponent_places']
    tables.append([
        titles['places_opponent'], descriptions['places_opponent'],
        table.common.places(opponent_places, matchups, True, False, n_last)])

    comparisons = cumulative_stats['comparisons']
    tables.append([
        titles['pairwise_matchup'], descriptions['pairwise_matchup'],
        table.categories.pairwise_comparisons(comparisons, matchups, False, n_last, _less_win_categories)])
    opponent_comparisons = cumulative_stats['opponent_comparisons']
    tables.append([
        titles['pairwise_matchup_opp'], descriptions['pairwise_matchup_opp'],
        table.categories.pairwise_comparisons(opponent_comparisons, matchups, True, n_last, _less_win_categories)])
    comparisons_h2h = cumulative_stats['comparisons_h2h']
    tables.append([
        titles['pairwise_h2h'], descriptions['pairwise_h2h'],
        table.common.h2h(comparisons_h2h)])

    if is_each_category:
        category_record = cumulative_stats['category_record']
        expected_category_record = cumulative_stats['expected_category_record']
        tables.append([
            titles['expected_cat'], descriptions['expected_cat'],
            table.categories.expected_category_stats(
                category_record, expected_category_record, matchups, _less_win_categories)])
    else:
        win_record = cumulative_stats['win_record']
        expected_win_record = cumulative_stats['expected_win_record']
        tables.append([
            titles['expected_win'], descriptions['expected_win'],
            table.categories.expected_win_stats(win_record, expected_win_record, matchups)])

    return tables


def _group_tables(group_settings, matchup, scoreboards, box_scores, global_resources):
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    is_each_category = group_settings['is_each_category']
    leagues = group_settings['leagues'].split(',')
    sports = group_settings['sports']
    tiebreaker = group_settings['tiebreaker']

    matchups = np.arange(1, matchup + 1)
    group_tables = []
    for league in leagues:
        league_box_scores = None if box_scores is None else box_scores[league]
        matchup_results_table = [
            titles['matchup'], descriptions['matchup'],
            _matchup_table(league, group_settings, matchup, scoreboards, league_box_scores)]

        scores, _, category_pairs, league_name = scoreboards[league]
        cumulative_stats = _cumulative_stats(matchup, scores, category_pairs, tiebreaker)
        cumulative_tables = _cumulative_tables(cumulative_stats, matchups, global_resources, is_each_category)
        plays_tables = _plays_tables(sports, matchups, league_box_scores, global_resources)

        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        league_tables = [matchup_results_table] + cumulative_tables + plays_tables
        group_tables.append([league_name, league_link, league_tables])

    return group_tables


def calculate_tables(group_settings, schedule, matchup, scoreboards, box_scores, global_resources):
    scoreboards_activated = utils.categories.apply_activation_scoreboards(
        scoreboards, box_scores, group_settings, schedule)
    group_tables = _group_tables(group_settings, matchup, scoreboards_activated, box_scores, global_resources)
    analytics_tables = _analytics_tables(group_settings, matchup, scoreboards_activated, global_resources)

    overall_tables = []
    leagues = group_settings['leagues'].split(',')
    if len(leagues) > 1:
        overall_stats = _overall_stats(group_settings, matchup, scoreboards_activated, box_scores)
        overall_tables = _overall_tables(group_settings, matchup, overall_stats, global_resources)

    return {
        'results': {'leagues': group_tables, 'overall_tables': overall_tables},
        'analytics': {'leagues': analytics_tables, 'overall_tables': []},
    }

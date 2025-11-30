from collections import defaultdict, Counter

import numpy as np

import table.analytics
import table.categories
import table.common
import utils.categories
import utils.common
import utils.data


_less_to_win_categories = ['TO', 'GAA', 'GA', 'PF']
_plays_cols = {'basketball': 'MIN', 'hockey': 'GP'}
_plays_getters = {'basketball': utils.data.minutes, 'hockey': utils.data.player_games}
_plays_names = {'basketball': 'minutes', 'hockey': 'games'}


def _analytics_tables(league_settings, schedule, matchup, scoreboards, box_scores, global_resources):
    leagues = league_settings['leagues'].split(',')
    analytics_enabled_flags = map(int, league_settings['is_analytics_enabled'].split(','))
    sports = league_settings['sports']

    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    category_names = global_resources['category_names']
    analytics_tables = []
    for is_analytics_enabled, league in zip(analytics_enabled_flags, leagues):
        if not is_analytics_enabled:
            continue

        _, team_names, category_pairs, league_name = scoreboards[league]
        gk_games_per_matchup = None
        if box_scores is not None:
            league_box_scores = box_scores[league]
            gk_games_per_matchup = []
            for m in range(matchup):
                matchup_gk_games = utils.data.goalkeeper_games(league_box_scores[m])
                gk_games_per_matchup.append(matchup_gk_games)
        categories, category_places, category_win_stats = utils.categories.get_each_category_stats(
            league_settings, schedule, matchup, category_pairs, gk_games_per_matchup, _less_to_win_categories)

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

        matchups = np.arange(1, matchup + 1)
        tables.append([
            titles['result_expectation_h2h'], descriptions['result_expectation_h2h'],
            table.analytics.power_predictions_h2h(category_places)])

        for cat in categories:
            cat_name = category_names[cat]
            places = category_places[cat]
            tables.append([
                titles['category_places'].format(cat_name), descriptions['category_places'].format(cat_name),
                table.common.places(places, matchups, False, False, n_last)])

        for team_id, team_name in sorted(team_names.items()):
            team_key = (team_name, team_id, league_name, league)
            tables.append([
                titles['team_category_record'].format(team_name), descriptions['team_category_record'],
                table.analytics.h2h_category_record(category_places, categories, team_key, n_last)])
            tables.append([
                titles['result_expectation'].format(team_name), descriptions['result_expectation'],
                table.analytics.power_predictions(category_places, team_key, matchups)])

        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        analytics_tables.append([league_name, league_link, tables])
    return analytics_tables


def _overall_tables(matchup, categories, plays, scores, stats_pairs, league_settings, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    tiebreaker = league_settings['tiebreaker']

    overall_tables = []
    plays_data = None
    if plays:
        plays_places = utils.common.get_places(plays, True)
        plays_data = (_plays_cols[league_settings['sports']], plays, plays_places)
    stats = utils.categories.get_stats(stats_pairs[matchup - 1])
    opponent_dict = utils.common.get_opponent_dict(stats_pairs[matchup - 1])
    places_data = utils.categories.get_places_data(stats, categories, _less_to_win_categories)
    comparisons = utils.categories.get_comparison_stats(stats, categories, _less_to_win_categories, tiebreaker)

    expected_score = utils.categories.get_expected_score(stats, categories, _less_to_win_categories)
    tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
        stats, categories, _less_to_win_categories, tiebreaker)
    expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opponent_dict)
    expectations = expected_score if league_settings['is_each_category'] else expected_result
    expectations_column_name = 'ExpScore' if league_settings['is_each_category'] else 'ER'
    metrics = {
        'Score': scores,
        expectations_column_name: expectations,
        'TP': comparisons,
    }
    overall_tables.append([
        titles['matchup_overall'], descriptions['matchup_overall'],
        table.categories.matchup(categories, stats, plays_data, places_data, _less_to_win_categories, metrics)])

    places = defaultdict(list)
    for m in range(matchup):
        matchup_places_sum = utils.categories.get_places_sum(stats_pairs[m], categories, _less_to_win_categories)
        places_sum_places = utils.common.get_places(matchup_places_sum, False)
        for team in places_sum_places:
            places[team].append(places_sum_places[team])
    overall_tables.append([
        titles['places_overall'], descriptions['places_overall'],
        table.common.places(places, np.arange(1, matchup + 1), False, True, n_last)])
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


def calculate_tables(league_settings, schedule, matchup, scoreboards, box_scores, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    is_each_category = league_settings['is_each_category']
    leagues = league_settings['leagues'].split(',')
    sports = league_settings['sports']
    tiebreaker = league_settings['tiebreaker']
    gk_threshold = league_settings['gk_threshold'] if 'gk_threshold' in league_settings else None
    is_playoffs_double_gk_threshold = league_settings.get('is_playoffs_double_gk_threshold', False)

    has_box_scores = box_scores is not None
    leagues_tables = []
    overall_plays = {} if has_box_scores else None
    overall_scores = []
    overall_stats_pairs = [[] for _ in range(matchup)]
    for league in leagues:
        scores, _, category_pairs, league_name = scoreboards[league]
        matchup_scores = scores[matchup - 1]
        overall_scores.extend(matchup_scores)
        
        plays = _plays_getters[sports](box_scores[league][matchup - 1]) if has_box_scores else None
        plays_places = utils.common.get_places(plays, reverse=True) if plays is not None else None
        gk_games = utils.data.goalkeeper_games(box_scores[league][matchup - 1]) if has_box_scores else None
        overall_plays = overall_plays | plays if plays is not None else overall_plays

        actual_gk_threshold = gk_threshold
        is_playoffs = schedule[matchup][-1]
        if is_playoffs_double_gk_threshold and is_playoffs:
            actual_gk_threshold = gk_threshold if gk_threshold is None else 2 * gk_threshold
        matchup_pairs, categories = category_pairs[matchup - 1]
        matchup_pairs = utils.categories.apply_gk_rules(matchup_pairs, gk_games, actual_gk_threshold)

        stats = utils.categories.get_stats(matchup_pairs)
        places_data = utils.categories.get_places_data(stats, categories, _less_to_win_categories)
        places_sum = {team: np.sum(team_places) for team, team_places in places_data.items()}
        stats_with_plays = utils.categories.join_stats_and_plays(stats, plays)
        places_with_plays = utils.categories.join_stats_and_plays(places_data, plays_places)
        plays_columns = [_plays_cols[league_settings['sports']]] if plays is not None else []
        categories_with_plays = plays_columns + categories

        matchup_expected_score = utils.categories.get_expected_score(stats, categories, _less_to_win_categories)
        matchup_tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
            stats, categories, _less_to_win_categories, tiebreaker)
        opponent_dict = utils.common.get_opponent_dict(matchup_pairs)
        matchup_expected_result = utils.categories.get_expected_result(
            matchup_expected_score, matchup_tiebreaker_stats, opponent_dict)
        matchup_expectations = matchup_expected_score \
            if league_settings['is_each_category'] else matchup_expected_result
        expectations_column_name = 'ExpScore' if league_settings['is_each_category'] else 'ER'
        comparisons = utils.categories.get_comparison_stats(stats, categories, _less_to_win_categories, tiebreaker)
        metrics = {
            'Score': matchup_scores,
            expectations_column_name: matchup_expectations,
            'TP': comparisons,
        }

        tables = []
        tables.append([
            titles['matchup'], descriptions['matchup'],
            table.categories.matchup(
                stats_with_plays, places_with_plays, places_sum,
                categories_with_plays, _less_to_win_categories, metrics)])

        places = defaultdict(list)
        opp_places = defaultdict(list)
        comparisons = defaultdict(list)
        opp_comparisons = defaultdict(list)
        expected_category_record = defaultdict(list)
        win_record = defaultdict(Counter)
        expected_win_record = defaultdict(list)
        comparisons_h2h = defaultdict(lambda: defaultdict(Counter))
        for m in range(matchup):
            current_matchup = m + 1
            gk_games = utils.data.goalkeeper_games(box_scores[league][m]) if has_box_scores else None
            actual_gk_threshold = gk_threshold
            is_playoffs = schedule[current_matchup][-1]
            if is_playoffs_double_gk_threshold and is_playoffs:
                actual_gk_threshold = gk_threshold if gk_threshold is None else 2 * gk_threshold

            stats_pairs, _ = category_pairs[m]
            stats_pairs = utils.categories.apply_gk_rules(stats_pairs, gk_games, actual_gk_threshold)
            opp_dict = utils.common.get_opponent_dict(stats_pairs)
            overall_stats_pairs[m].extend(stats_pairs)
            
            matchup_places_sum = utils.categories.get_places_sum(stats_pairs, categories, _less_to_win_categories)
            matchup_places = utils.common.get_places(matchup_places_sum, False)
            for team in matchup_places:
                places[team].append(matchup_places[team])
                opp_places[team].append(matchup_places[opp_dict[team]])
            
            stats = utils.categories.get_stats(stats_pairs)
            comparison_stats = utils.categories.get_comparison_stats(
                stats, categories, _less_to_win_categories, tiebreaker)
            for team in comparison_stats:
                comparisons[team].append('-'.join(map(str, comparison_stats[team])))
                opp_comparisons[team].append('-'.join(map(str, comparison_stats[opp_dict[team]])))
            
            for team in opp_dict:
                result = utils.categories.get_pair_result(
                    stats[team], stats[opp_dict[team]], categories, _less_to_win_categories, tiebreaker)
                win_record[team][result] += 1

            expected_score = utils.categories.get_expected_score(stats, categories, _less_to_win_categories)
            tiebreaker_stats = utils.categories.get_tiebreaker_expectation(
                stats, categories, _less_to_win_categories, tiebreaker)
            expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opp_dict)

            for team in expected_score:
                expected_category_record[team].append(expected_score[team])
                expected_win_record[team].append(expected_result[team])

            tiebreaker = league_settings['tiebreaker']
            for team in stats:
                for opp in stats:
                    if team == opp:
                        continue
                    h2h_res = utils.categories.get_pair_result(
                        stats[team], stats[opp], categories, _less_to_win_categories, tiebreaker)
                    comparisons_h2h[team][opp][h2h_res] += 1

        matchups = np.arange(1, matchup + 1)
        tables.append([
            titles['places'], descriptions['places'],
            table.common.places(places, matchups, False, False, n_last)])
        tables.append([
            titles['places_opponent'], descriptions['places_opponent'],
            table.common.places(opp_places, matchups, True, False, n_last)])

        tables.append([
            titles['pairwise_matchup'], descriptions['pairwise_matchup'],
            table.categories.pairwise_comparisons(comparisons, matchups, False, n_last, _less_to_win_categories)])
        tables.append([
            titles['pairwise_matchup_opp'], descriptions['pairwise_matchup_opp'],
            table.categories.pairwise_comparisons(opp_comparisons, matchups, True, n_last, _less_to_win_categories)])
        tables.append([
            titles['pairwise_h2h'], descriptions['pairwise_h2h'],
            table.common.h2h(comparisons_h2h)])

        if is_each_category:
            category_record = {}
            for m in range(matchup):
                for sc in scores[m]:
                    for i in range(len(sc)):
                        if sc[i][0] not in category_record:
                            category_record[sc[i][0]] = np.array(list(map(float, sc[i][1].split('-'))))
                        else:
                            category_record[sc[i][0]] += np.array(list(map(float, sc[i][1].split('-'))))
            tables.append([
                titles['expected_cat'], descriptions['expected_cat'],
                table.categories.expected_category_stats(
                    category_record, expected_category_record, matchup, _less_to_win_categories)])
        else:
            tables.append([
                titles['expected_win'], descriptions['expected_win'],
                table.categories.expected_win_stats(win_record, expected_win_record, matchups)])
        
        league_box_scores = box_scores[league] if has_box_scores else None
        plays_tables = _plays_tables(sports, matchups, league_box_scores, global_resources)
        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        leagues_tables.append([league_name, league_link, tables + plays_tables])

    analytics_tables = _analytics_tables(
        league_settings, schedule, matchup, scoreboards, box_scores, global_resources)
    overall_tables = []
    if len(leagues) > 1:
        overall_tables = _overall_tables(matchup, categories, overall_plays,
            overall_scores, overall_stats_pairs, league_settings)

    return {
        'results': {'leagues': leagues_tables, 'overall_tables': overall_tables},
        'analytics': {'leagues': analytics_tables, 'overall_tables': []},
    }

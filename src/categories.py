from collections import defaultdict, Counter

import numpy as np

import table.analytics
import table.categories
import table.common
import utils.categories
import utils.common
import utils.data


_gk_category_lowers = {'GAA': np.inf, 'SV%': -np.inf, 'GA': np.inf}
_less_to_win_categories = ['TO', 'GAA', 'GA', 'PF']
_plays_cols = {'basketball': 'MIN', 'hockey': 'GP'}


def _apply_gk_rules(matchup_pairs, gk_games, gk_threshold):
    pairs_updated = []
    for pair in matchup_pairs:
        updated_pair = []
        for team, player_stats in pair:
            updated_player_stats = []
            for cat, stat in player_stats:
                if cat in _gk_category_lowers and gk_games and team in gk_games and gk_games[team] < gk_threshold:
                    updated_player_stats.append((cat, _gk_category_lowers[cat]))
                else:
                    updated_player_stats.append((cat, stat))
            updated_pair.append((team, updated_player_stats))
        pairs_updated.append(tuple(updated_pair))

    return pairs_updated


def _get_each_category_stats(league, league_settings, schedule, matchup, category_pairs, box_scores_data):
    gk_threshold = league_settings['gk_threshold'] if 'gk_threshold' in league_settings else None
    double_gk_threshold_key = 'is_playoffs_double_gk_threshold'
    is_playoffs_double_gk_threshold = league_settings[double_gk_threshold_key] \
        if double_gk_threshold_key in league_settings else False

    each_category_places = defaultdict(lambda: defaultdict(list))
    each_category_win_stats = defaultdict(lambda: defaultdict(list))
    for m in range(matchup):
        current_matchup = m + 1
        gk_games = None
        if league_settings['is_full_support']:
            matchup_box_scores_data = box_scores_data[league][m]
            gk_games = utils.data.gk_games(matchup_box_scores_data)

        actual_gk_threshold = gk_threshold
        is_playoffs = schedule[current_matchup][-1]
        if is_playoffs_double_gk_threshold and is_playoffs:
            actual_gk_threshold = gk_threshold if gk_threshold is None else 2 * gk_threshold
        matchup_pairs, categories = category_pairs[m]
        matchup_pairs = _apply_gk_rules(matchup_pairs, gk_games, actual_gk_threshold)
        opp_dict = utils.common.get_opponent_dict(matchup_pairs)
        stats = utils.categories.get_stats(matchup_pairs)
        places_data = utils.categories.get_places_data(stats, categories, _less_to_win_categories)
        for team in places_data:
            for cat, place, opp_place in zip(categories, places_data[team], places_data[opp_dict[team]]):
                each_category_places[cat][team].append(place)
                win_stat = (np.sign(opp_place - place) + 1) / 2 # 1 for win, 0.5 for draw, 0 for lose
                each_category_win_stats[cat][team].append(win_stat)

    return categories, each_category_places, each_category_win_stats


def _export_analytics_tables(league_settings, schedule, matchup, scoreboard_data, box_scores_data, global_resources):
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
    
        _, team_names, category_pairs, league_name = scoreboard_data[league]
        categories, each_category_places, each_category_win_stats = _get_each_category_stats(
            league, league_settings, schedule, matchup, category_pairs, box_scores_data
        )
            
        tables = []
        tables.append([
            titles['category_win_stats'], descriptions['category_win_stats'],
            table.analytics.win_stats_by_each_category(each_category_win_stats, categories)])
        tables.append([
            titles['recent_category_win_stats'].format(n_last),
            descriptions['recent_category_win_stats'].format(n_last),
            table.analytics.win_stats_by_each_category(each_category_win_stats, categories, n_last)
        ])
        tables.append([
            titles['category_power'], descriptions['category_power'],
            table.analytics.category_power(each_category_places, categories)])
        tables.append([
            titles['recent_category_power'].format(n_last),
            descriptions['recent_category_power'].format(n_last),
            table.analytics.category_power(each_category_places, categories, n_last)
        ])
        tables.append([
            titles['category_rankings'], descriptions['category_rankings'],
            table.analytics.category_rankings(each_category_places, categories)])

        matchups = np.arange(1, matchup + 1)
        tables.append([
            titles['result_expectation_h2h'], descriptions['result_expectation_h2h'],
            table.analytics.power_predictions_h2h(each_category_places)])

        for cat in categories:
            cat_name = category_names[cat]
            places = each_category_places[cat]
            tables.append([
                titles['category_places'].format(cat_name),
                descriptions['category_places'].format(cat_name),
                table.common.places(places, matchups, False, False, n_last)
            ])

        for team_id, team_name in sorted(team_names.items()):
            team_key = (team_name, team_id, league_name, league)
            tables.append([
                titles['team_category_record'].format(team_name), descriptions['team_category_record'],
                table.analytics.h2h_category_record(each_category_places, categories, team_key, n_last)])
            tables.append([
                titles['result_expectation'].format(team_name), descriptions['result_expectation'],
                table.analytics.power_predictions(each_category_places, team_key, matchups)])

        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        analytics_tables.append([league_name, league_link, tables])
    return analytics_tables


def _export_overall_tables(matchup, categories, plays, scores, stats_pairs, league_settings, global_resources):
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
    opp_dict = utils.common.get_opponent_dict(stats_pairs[matchup - 1])
    places_data = utils.categories.get_places_data(stats, categories, _less_to_win_categories)
    comparisons = utils.categories.get_comparison_stats(stats, categories, _less_to_win_categories, tiebreaker)

    expected_score = utils.categories.get_expected_score(stats, categories, _less_to_win_categories)
    tiebreaker_stats = utils.categories.get_tiebreaker_stats(stats, categories, _less_to_win_categories, tiebreaker)
    expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opp_dict)
    expected_data = expected_score if league_settings['is_each_category'] else expected_result

    overall_tables.append([
        titles['matchup_overall'], descriptions['matchup_overall'],
        table.categories.matchup(
            categories, stats, scores, plays_data, places_data, comparisons, expected_data,
            n_last, _less_to_win_categories)])

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


def export_reports(league_settings, schedule, matchup, scoreboard_data, box_scores_data, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    plays_getters = {'basketball': utils.data.minutes, 'hockey': utils.data.player_games}
    is_each_category = league_settings['is_each_category']
    leagues = league_settings['leagues'].split(',')
    leagues_names = []
    sports = league_settings['sports']
    tiebreaker = league_settings['tiebreaker']
    is_full_support = league_settings['is_full_support']
    gk_threshold = league_settings['gk_threshold'] if 'gk_threshold' in league_settings else None
    double_gk_threshold_key = 'is_playoffs_double_gk_threshold'
    is_playoffs_double_gk_threshold = league_settings[double_gk_threshold_key] \
        if double_gk_threshold_key in league_settings else False

    leagues_tables = []
    overall_plays = {} if is_full_support else None
    overall_scores = []
    overall_stats_pairs = [[] for _ in range(matchup)]
    for league in leagues:
        scores, _, category_pairs, league_name = scoreboard_data[league]
        leagues_names.append(league_name)
        scores_data = scores[matchup - 1]
        overall_scores.extend(scores_data)
        
        plays = None
        gk_games = None
        if is_full_support:
            matchup_box_scores_data = box_scores_data[league][matchup - 1]
            plays = plays_getters[sports](matchup_box_scores_data)
            if plays:
                overall_plays.update(plays)
            gk_games = utils.data.gk_games(matchup_box_scores_data)
        plays_data = None
        if plays:
            plays_places = utils.common.get_places(plays, True)
            plays_data = (_plays_cols[sports], plays, plays_places)
        
        actual_gk_threshold = gk_threshold
        is_playoffs = schedule[matchup][-1]
        if is_playoffs_double_gk_threshold and is_playoffs:
            actual_gk_threshold = gk_threshold if gk_threshold is None else 2 * gk_threshold
        matchup_pairs, categories = category_pairs[matchup - 1]
        matchup_pairs = _apply_gk_rules(matchup_pairs, gk_games, actual_gk_threshold)
        stats = utils.categories.get_stats(matchup_pairs)
        opp_dict = utils.common.get_opponent_dict(matchup_pairs)
        places_data = utils.categories.get_places_data(stats, categories, _less_to_win_categories)
        comparisons = utils.categories.get_comparison_stats(stats, categories, _less_to_win_categories, tiebreaker)

        matchup_expected_score = utils.categories.get_expected_score(stats, categories, _less_to_win_categories)
        matchup_tiebreaker_stats = utils.categories.get_tiebreaker_stats(
            stats, categories, _less_to_win_categories, tiebreaker)
        matchup_expected_result = utils.categories.get_expected_result(
            matchup_expected_score, matchup_tiebreaker_stats, opp_dict)
        matchup_expected_data = matchup_expected_score \
            if league_settings['is_each_category'] else matchup_expected_result

        tables = []
        tables.append([
            titles['matchup'], descriptions['matchup'],
            table.categories.matchup(
                categories, stats, scores_data, plays_data, places_data, comparisons, matchup_expected_data,
                n_last, _less_to_win_categories)])

        places = defaultdict(list)
        opp_places = defaultdict(list)
        comparisons = defaultdict(list)
        opp_comparisons = defaultdict(list)
        expected_each_category_stats = defaultdict(list)
        win_record = defaultdict(Counter)
        expected_win_record = defaultdict(list)
        comparisons_h2h = defaultdict(lambda: defaultdict(Counter))
        for m in range(matchup):
            current_matchup = m + 1
            gk_games = None
            if is_full_support:
                matchup_box_scores_data = box_scores_data[league][m]
                gk_games = utils.data.gk_games(matchup_box_scores_data)
            
            actual_gk_threshold = gk_threshold
            is_playoffs = schedule[current_matchup][-1]
            if is_playoffs_double_gk_threshold and is_playoffs:
                actual_gk_threshold = gk_threshold if gk_threshold is None else 2 * gk_threshold
            stats_pairs, _ = category_pairs[m]
            stats_pairs = _apply_gk_rules(stats_pairs, gk_games, actual_gk_threshold)
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
            tiebreaker_stats = utils.categories.get_tiebreaker_stats(stats, categories, _less_to_win_categories, tiebreaker)
            expected_result = utils.categories.get_expected_result(expected_score, tiebreaker_stats, opp_dict)

            for team in expected_score:
                expected_each_category_stats[team].append(expected_score[team])
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
            titles['places_opp'], descriptions['places_opp'],
            table.common.places(opp_places, matchups, True, False, n_last)])

        tables.append([
            titles['pairwise_matchup'], descriptions['pairwise_matchup'],
            table.categories.comparisons(comparisons, matchups, False, n_last, _less_to_win_categories)])
        tables.append([
            titles['pairwise_matchup_opp'], descriptions['pairwise_matchup_opp'],
            table.categories.comparisons(opp_comparisons, matchups, True, n_last, _less_to_win_categories)])
        tables.append([
            titles['pairwise_h2h'], descriptions['pairwise_h2h'],
            table.common.h2h(comparisons_h2h)])
        if is_each_category:
            each_category_stats = {}
            for m in range(matchup):
                for sc in scores[m]:
                    for i in range(len(sc)):
                        if sc[i][0] not in each_category_stats:
                            each_category_stats[sc[i][0]] = np.array(list(map(float, sc[i][1].split('-'))))
                        else:
                            each_category_stats[sc[i][0]] += np.array(list(map(float, sc[i][1].split('-'))))
            table_stats = (each_category_stats, expected_each_category_stats)
            tables.append([
                titles['expected_cat'], descriptions['expected_cat'],
                table.categories.expected_each_category_stats(*table_stats, matchup, n_last, _less_to_win_categories)])
        else:
            tables.append([
                titles['expected_win'], descriptions['expected_win'],
                table.categories.expected_win_stats(win_record, expected_win_record, matchups)])
        
        if is_full_support:
            plays = defaultdict(list)
            plays_places = defaultdict(list)
            has_plays = False
            for m in range(matchup):
                current_matchup = m + 1
                matchup_box_scores_data = box_scores_data[league][m]
                plays_matchup = plays_getters[sports](matchup_box_scores_data)
                if plays_matchup:
                    has_plays = True
                    for team, value in plays_matchup.items():
                        plays[team].append(value)
                    matchup_places = utils.common.get_places(plays_matchup, True)
                    for team, value in matchup_places.items():
                        plays_places[team].append(value)
            if has_plays:
                key_dict = {'basketball': 'minutes', 'hockey': 'games'}
                table_key = key_dict[sports]
                tables.append([
                    titles[table_key], descriptions[table_key],
                    table.common.scores(plays, matchups, False, n_last)])
                tables.append([
                    titles[f'{table_key}_places'], descriptions[f'{table_key}_places'],
                    table.common.places(plays_places, matchups, False, False, n_last)])

        league_link = f'https://fantasy.espn.com/{sports}/league?leagueId={league}'
        leagues_tables.append([league_name, league_link, tables])

    analytics_tables = _export_analytics_tables(
        league_settings, schedule, matchup, scoreboard_data, box_scores_data, global_resources)
    overall_tables = []
    if len(leagues) > 1:
        overall_tables = _export_overall_tables(matchup, categories, overall_plays,
            overall_scores, overall_stats_pairs, league_settings)
    global_config = global_resources['config']
    utils.common.save_tables(
        sports, leagues_tables, overall_tables, leagues[0], leagues_names[0],
        matchup, schedule, global_config, 'results')
    utils.common.save_tables(
        sports, analytics_tables, [], leagues[0], leagues_names[0], matchup, schedule, global_config, 'analytics')

from collections import Counter, defaultdict

import numpy as np

import utils.common
import utils.data


_gk_category_lowers = {'GAA': np.inf, 'SV%': -np.inf, 'GA': np.inf}


def _get_category_expectation(score_pairs, category, less_win_categories):
    scores = np.array([score for _, score in score_pairs])
    norm_coeff = len(scores) - 1
    result = {}
    for team, sc in score_pairs:
        counts = np.array([np.sum(scores < sc), np.sum(scores > sc), np.sum(scores == sc) - 1])
        res_slice = [1, 0, 2] if category in less_win_categories else [0, 1, 2]
        result[team] = counts[res_slice] / norm_coeff
    return result


def get_each_category_stats(matchup, category_pairs, less_win_categories):
    category_places = defaultdict(lambda: defaultdict(list))
    category_win_stats = defaultdict(lambda: defaultdict(list))
    for m in range(matchup):
        matchup_pairs, categories = category_pairs[m]
        opponent_dict = utils.common.get_opponent_dict(matchup_pairs)
        stats = get_stats(matchup_pairs)
        places_data = get_places_data(stats, categories, less_win_categories)
        for team in places_data:
            for cat, place, opponent_place in zip(categories, places_data[team], places_data[opponent_dict[team]]):
                category_places[cat][team].append(place)
                win_stat = (np.sign(opponent_place - place) + 1) / 2 # 1 for win, 0.5 for draw, 0 for lose
                category_win_stats[cat][team].append(win_stat)

    return categories, category_places, category_win_stats


def get_comparison_stats(stats, categories, less_win_categories, tiebreaker):
    comparison_stats = {}
    for team in stats:
        win_stat = Counter()
        for opp in stats:
            if opp != team:
                fake_result, _ = get_pair_result(stats[team], stats[opp], categories, less_win_categories, tiebreaker)
                win_stat[fake_result] += 1
        comparison_stats[team] = [win_stat['W'], win_stat['L'], win_stat['D']]
    return comparison_stats


def get_expected_score(stats, categories, less_win_categories):
    expected_score = {team: np.array([0.0, 0.0, 0.0]) for team in stats}
    for i, cat in enumerate(categories):
        pairs = [(team, stats[team][i]) for team in stats]
        expected_stats = _get_category_expectation(pairs, cat, less_win_categories)
        for team in expected_stats:
            expected_score[team] += expected_stats[team]
    return expected_score


def get_tiebreaker_expectation(stats, categories, less_win_categories, tiebreaker):
    if tiebreaker not in categories:
        return {team: np.array([0.0, 0.0, 0.0]) for team in stats}

    tiebreaker_index = categories.index(tiebreaker)
    pairs = [(team, stats[team][tiebreaker_index]) for team in stats]
    tiebreaker_stats = _get_category_expectation(pairs, tiebreaker, less_win_categories)
    return tiebreaker_stats


def get_expected_result(expected_score, tiebreaker_stats, opponents_dict):
    expected_result = {}
    for team in expected_score:
        team_score = list(expected_score[team][[0, 2, 1]])
        opponent_score = list(expected_score[opponents_dict[team]][[0, 2, 1]])
        if team_score != opponent_score:
            expected_result[team] = 'W' if team_score > opponent_score else 'L'
        else:
            team_tiebreaker_score = list(tiebreaker_stats[team][[0, 2, 1]])
            opponent_tiebreaker_score = list(tiebreaker_stats[opponents_dict[team]][[0, 2, 1]])
            if team_tiebreaker_score != opponent_tiebreaker_score:
                expected_result[team] = 'W' if team_tiebreaker_score > opponent_tiebreaker_score else 'L'
            else:
                expected_result[team] = 'D'
    return expected_result


def get_pair_result(team_stats, opponent_stats, categories, less_win_categories, tiebreaker):
    win_count = 0
    lose_count = 0
    for index, cat in enumerate(categories):
        cat_value_coeff = 1.0 if cat != tiebreaker else 1.01
        if team_stats[index] > opponent_stats[index]:
            lose_count += (cat in less_win_categories) * cat_value_coeff
            win_count += (cat not in less_win_categories) * cat_value_coeff
        elif team_stats[index] < opponent_stats[index]:
            lose_count += (cat not in less_win_categories) * cat_value_coeff
            win_count += (cat in less_win_categories)  * cat_value_coeff
    team_result = 'D' if win_count == lose_count else 'W' if win_count > lose_count else 'L'
    opponent_result = 'D' if win_count == lose_count else 'L' if win_count > lose_count else 'W'
    return team_result, opponent_result


def get_places_data(stats, categories, less_win_categories):
    places_data = defaultdict(list)
    for index, cat in enumerate(categories):
        cat_scores = {team: stats[team][index] for team in stats}
        places = utils.common.get_places(cat_scores, cat not in less_win_categories)
        for team in places:
            places_data[team].append(places[team])
    return places_data


def get_places_sum(matchup_pairs, categories, less_win_categories):
    stats = get_stats(matchup_pairs)
    places_data = get_places_data(stats, categories, less_win_categories)
    return {team: np.sum(places_data[team]) for team in places_data}


def get_stats(results):
    stats = {}
    for pair in results:
        for team, total_score in pair:
            stats[team] = [score for _, score in total_score]
    return stats


def join_stats_and_plays(stats, plays):
    if plays is None:
        return stats

    return {team: [plays[team]] + team_stats for team, team_stats in stats.items()}


def calculate_category_record(scores):
    category_record = {}
    for matchup_scores in scores:
        for scores_pair in matchup_scores:
            for team_key, team_score in scores_pair:
                if team_key in category_record:
                    category_record[team_key] += np.array(list(map(float, team_score.split('-'))))
                else:
                    category_record[team_key] = np.array(list(map(float, team_score.split('-'))))

    return category_record


def _apply_activation_pairs(matchup_pairs, matchup, settings, stats):
    if settings is None or stats is None:
        return matchup_pairs

    gk_threshold = settings['goalkeeper_games'][matchup]
    gk_games = stats['goalkeeper_games'][matchup]

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


def _activation_settings(group_settings, matchups, schedule):
    if 'gk_threshold' not in group_settings:
        return None

    gk_threshold = group_settings['gk_threshold']
    is_playoffs_double_gk_games = group_settings.get('is_playoffs_double_gk_games', False)

    if is_playoffs_double_gk_games:
        gk_games_thresholds = {m: 2 * gk_threshold if schedule[m][-1] else gk_threshold for m in matchups}
    else:
        gk_games_thresholds = {m: gk_threshold for m in matchups}
    return {'goalkeeper_games': gk_games_thresholds}


def _activation_stats(league_box_scores, matchups):
    if league_box_scores is None:
        return None

    return {
        'goalkeeper_games': {m: utils.data.goalkeeper_games(league_box_scores[m-1]) for m in matchups}
    }


def apply_activation_scoreboards(scoreboards, box_scores, group_settings, schedule):
    scoreboards_activated = {}
    for league, league_scoreboards in scoreboards.items():
        scores, team_names, category_pairs, league_name = league_scoreboards
        matchup = len(category_pairs)

        matchups = np.arange(1, matchup + 1)
        league_box_scores = None if box_scores is None else box_scores[league]
        settings = _activation_settings(group_settings, matchups, schedule)
        stats = _activation_stats(league_box_scores, matchups)

        category_pairs_activated = []
        for m, (pairs, categories) in enumerate(category_pairs):
            pairs_activated = _apply_activation_pairs(pairs, m + 1, settings, stats)
            category_pairs_activated.append((pairs_activated, categories))

        scoreboards_activated[league] = scores, team_names, category_pairs_activated, league_name

    return scoreboards_activated

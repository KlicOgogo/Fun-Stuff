from collections import Counter, defaultdict

import numpy as np

import utils.common


def _get_expected_category_probs(score_pairs, category, less_to_win_categories):
    scores = np.array([score for _, score in score_pairs])
    norm_coeff = len(scores) - 1
    result = {}
    for team, sc in score_pairs:
        counts = np.array([np.sum(scores < sc), np.sum(scores > sc), np.sum(scores == sc) - 1])
        res_slice = [1, 0, 2] if category in less_to_win_categories else [0, 1, 2]
        result[team] = counts[res_slice] / norm_coeff
    return result


def get_comparison_stats(stats, categories, less_to_win_categories, tiebreaker):
    comparison_stats = {}
    for team in stats:
        win_stat = Counter()
        for opp in stats:
            if opp != team:
                fake_result = get_pair_result(stats[team], stats[opp], categories, less_to_win_categories, tiebreaker)
                win_stat[fake_result] += 1
        comparison_stats[team] = [win_stat['W'], win_stat['L'], win_stat['D']]
    return comparison_stats


def get_expected_score_and_result(stats, opponents_dict, categories, less_to_win_categories, tiebreaker):
    expected_score = {team: np.array([0.0, 0.0, 0.0]) for team in stats}
    tiebreaker_stats = {team: np.array([0.0, 0.0, 0.0]) for team in stats}
    for i, cat in enumerate(categories):
        pairs = [(team, stats[team][i]) for team in stats]
        expected_stats = _get_expected_category_probs(pairs, cat, less_to_win_categories)
        if cat == tiebreaker:
            tiebreaker_stats = expected_stats
        for team in expected_stats:
            expected_score[team] += expected_stats[team]
    
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
    return expected_score, expected_result


def get_pair_result(team_stat, opp_stat, categories, less_to_win_categories, tiebreaker):
    win_count = 0
    lose_count = 0
    for index, cat in enumerate(categories):
        cat_value_coeff = 1.0 if cat != tiebreaker else 1.01
        if team_stat[index] > opp_stat[index]:
            lose_count += (cat in less_to_win_categories) * cat_value_coeff
            win_count += (cat not in less_to_win_categories) * cat_value_coeff
        elif team_stat[index] < opp_stat[index]:
            lose_count += (cat not in less_to_win_categories) * cat_value_coeff
            win_count += (cat in less_to_win_categories)  * cat_value_coeff
    result = 'D' if win_count == lose_count else 'W' if win_count > lose_count else 'L'
    return result


def get_places_data(stats, categories, less_to_win_categories):
    places_data = defaultdict(list)
    for index, cat in enumerate(categories):
        cat_scores = {team: stats[team][index] for team in stats}
        places = utils.common.get_places(cat_scores, cat not in less_to_win_categories)
        for team in places:
            places_data[team].append(places[team])
    return places_data


def get_places_sum(matchup_pairs, categories, less_to_win_categories):
    stats = get_stats(matchup_pairs)
    places_data = get_places_data(stats, categories, less_to_win_categories)
    return {team: np.sum(places_data[team]) for team in places_data}


def get_stats(results):
    stats = {}
    for pair in results:
        for team, total_score in pair:
            stats[team] = [score for _, score in total_score]
    return stats

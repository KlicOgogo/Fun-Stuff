from collections import Counter, defaultdict

import numpy as np

import utils.common


def _calculate_luck_score(pairs, places):
    luck = {}
    place_threshold = len(places) / 2
    for p1, p2 in pairs:
        if p1[1] != p2[1]:
            winner, looser = (p1[0], p2[0]) if p1[1] > p2[1] else (p2[0], p1[0])
            luck[winner] = max(0, places[winner] - place_threshold)
            luck[looser] = min(0, places[looser] - place_threshold - 1)
        else:
            score_extra_sub = 0 if places[p1[0]] > place_threshold else 1
            luck[p1[0]] = (places[p1[0]] - place_threshold - score_extra_sub) / 2
            luck[p2[0]] = (places[p1[0]] - place_threshold - score_extra_sub) / 2
    return luck


def calculate_pairwise_h2h(scores):
    pairwise_h2h = defaultdict(lambda: defaultdict(Counter))
    scores_np = {team: np.array(scores[team]) for team in scores}

    for team in scores:
        for opponent in scores:
            if team == opponent:
                continue

            team_scores = scores_np[team]
            opponent_scores = scores_np[opponent]

            pairwise_h2h[team][opponent]['W'] = (team_scores > opponent_scores).sum()
            pairwise_h2h[team][opponent]['L'] = (team_scores < opponent_scores).sum()
            pairwise_h2h[team][opponent]['D'] = (team_scores == opponent_scores).sum()

    return pairwise_h2h


def calculate_scores_metrics(scores_pairs, matchups):
    metrics = {
        'opponent_scores': defaultdict(list),
        'luck': defaultdict(list),
        'opponent_luck': defaultdict(list),
        'places': defaultdict(list),
        'opponent_places': defaultdict(list),
    }

    opponent_scores = metrics['opponent_scores']
    for m in matchups:
        matchup_results = scores_pairs[m]
        for p1, p2 in matchup_results:
            opponent_scores[p1[0]].append(p2[1])
            opponent_scores[p2[0]].append(p1[1])

    for m in matchups:
        matchup_results = scores_pairs[m]
        matchup_scores = {team: score for pair in matchup_results for team, score in pair}
        matchup_places = utils.common.get_places(matchup_scores, True)
        opp_dict = utils.common.get_opponent_dict(matchup_results)

        for team in matchup_places:
            metrics['places'][team].append(matchup_places[team])
            metrics['opponent_places'][team].append(matchup_places[opp_dict[team]])

        matchup_luck = _calculate_luck_score(matchup_results, matchup_places)
        for team in matchup_luck:
            metrics['luck'][team].append(matchup_luck[team])
            metrics['opponent_luck'][team].append(matchup_luck[opp_dict[team]])

    return metrics

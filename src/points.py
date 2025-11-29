from collections import defaultdict, Counter

import numpy as np

import table.common
import table.points
import utils.common
import utils.data
import utils.points


_plays_per_game = {'basketball': 30, 'hockey': 1}
_plays_names = {'basketball': 'minutes', 'hockey': 'games'}


def _league_scores_tables(matchup, scores, scores_pairs, global_resources):
    tables = []
    opp_scores = defaultdict(list)
    luck = defaultdict(list)
    opp_luck = defaultdict(list)
    places = defaultdict(list)
    opp_places = defaultdict(list)
    for matchup_results in scores_pairs[:matchup]:
        for p1, p2 in matchup_results:
            opp_scores[p1[0]].append(p2[1])
            opp_scores[p2[0]].append(p1[1])

        matchup_scores = {team: score for pair in matchup_results for team, score in pair}
        matchup_places = utils.common.get_places(matchup_scores, True)
        opp_dict = utils.common.get_opponent_dict(matchup_results)
        for team in matchup_places:
            places[team].append(matchup_places[team])
            opp_places[team].append(matchup_places[opp_dict[team]])
        matchup_luck = utils.points.get_luck_score(matchup_results, matchup_places)
        for team in matchup_luck:
            luck[team].append(matchup_luck[team])
            opp_luck[team].append(matchup_luck[opp_dict[team]])
    
    matchups = np.arange(1, matchup + 1)
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    tables.append([
        titles['scores'], descriptions['scores'],
        table.common.scores(scores, matchups, False, n_last)])
    tables.append([
        titles['scores_opp'], descriptions['scores_opp'],
        table.common.scores(opp_scores, matchups, True, n_last)])
    tables.append([
        titles['luck'], descriptions['luck'],
        table.points.luck_score(luck, matchups, False, n_last)])
    tables.append([
        titles['luck_opp'], descriptions['luck_opp'],
        table.points.luck_score(opp_luck, matchups, True, n_last)])
    tables.append([
        titles['places'], descriptions['places'],
        table.common.places(places, matchups, False, False, n_last)])
    tables.append([
        titles['places_opp'], descriptions['places_opp'],
        table.common.places(opp_places, matchups, True, False, n_last)])
    
    pairwise_h2h = defaultdict(lambda: defaultdict(Counter))
    for team in scores:
        for opponent in scores:
            if team == opponent:
                continue
            team_scores = np.array(scores[team])
            opponent_scores = np.array(scores[opponent])
            pairwise_h2h[team][opponent]['W'] = (team_scores > opponent_scores).sum()
            pairwise_h2h[team][opponent]['L'] = (team_scores < opponent_scores).sum()
            pairwise_h2h[team][opponent]['D'] = (team_scores == opponent_scores).sum()
    tables.append([
        titles['pairwise_h2h'], descriptions['pairwise_h2h'],
        table.common.h2h(pairwise_h2h)])

    return tables


def _league_plays_tables(sports, matchup, scores, plays, plays_places, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    plays_name = _plays_names[sports]
    matchups = np.arange(1, matchup + 1)
    tables = []
    tables.append([
        titles[plays_name], descriptions[plays_name],
        table.common.scores(plays, matchups, False, n_last)])
    tables.append([
        titles[f'{plays_name}_places'], descriptions[f'{plays_name}_places'],
        table.common.places(plays_places, matchups, False, False, n_last)])

    mean_scores = {}
    for team in scores:
        scores_row = np.array(scores[team])
        plays_row = np.array(plays[team])
        mean_scores[team] = list(np.round(scores_row / plays_row * _plays_per_game[sports], 2))
    tables.append([
        titles['mean'], descriptions['mean'],
        table.common.scores(mean_scores, matchups, False, n_last)])

    mean_scores_places = defaultdict(list)
    for m in matchups:
        matchup_mean_scores = {team: scores[m-1] for team, scores in mean_scores.items()}
        matchup_places = utils.common.get_places(matchup_mean_scores, True)
        for team, value in matchup_places.items():
            mean_scores_places[team].append(value)
    tables.append([
        titles['mean_places'], descriptions['mean_places'],
        table.common.places(mean_scores_places, matchups, False, False, n_last)])

    return tables


def _export_overall_tables(n_leagues, matchup, overall_scores, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']

    overall_tables = []
    if n_leagues > 1:
        overall_places = defaultdict(list)
        for i in range(matchup):
            matchup_overall_scores = {team: overall_scores[team][i] for team in overall_scores}
            matchup_overall_places = utils.common.get_places(matchup_overall_scores, True)
            for team in matchup_overall_places:
                overall_places[team].append(matchup_overall_places[team])
        overall_tables.append([
            titles['places_overall'], descriptions['places_overall'],
            table.common.places(overall_places, np.arange(1, matchup + 1), False, True, n_last)])

    n_top = int(len(overall_scores) / n_leagues)
    top_common_cols = ['Team', 'Score', 'League']
    
    last_matchup_scores = [(team[0], overall_scores[team][-1], team[2]) for team in overall_scores]
    overall_tables.append([
        titles['best_matchup'], descriptions['best_matchup'],
        table.points.top(last_matchup_scores, n_top, top_common_cols, n_leagues == 1)])
    
    each_matchup_scores = []
    for team in overall_scores:
        team_scores = [(team[0], score, team[2], index + 1) for index, score in enumerate(overall_scores[team])]
        each_matchup_scores.extend(team_scores)
    overall_tables.append([
        titles['best_season'], descriptions['best_season'],
        table.points.top(each_matchup_scores, n_top, top_common_cols + ['Matchup'], n_leagues == 1)])
    
    if n_leagues > 1:
        totals = [(team[0], np.sum(scores), team[2], scores[-1]) for team, scores in overall_scores.items()]
        overall_tables.append([
            titles['best_season_total'], descriptions['best_season_total'],
            table.points.top(totals, n_top, top_common_cols + ['Last matchup'], False)])

    if n_leagues > 1 and n_top > 8:
        leagues_sums = defaultdict(list)
        for team, scores in overall_scores.items():
            leagues_sums[(team[2], team[3])].append(np.sum(scores))
        leagues_sums_list = []
        for league, sums in leagues_sums.items():
            leagues_sums_list.append((league[0], np.mean(sums), np.mean(list(sorted(sums, reverse=True))[:8])))
        overall_tables.append([
            titles['mean_season_total'], descriptions['mean_season_total'],
            table.points.top(leagues_sums_list, len(leagues_sums_list), ['League', 'Score', 'Top 8 score'], False)])
    return overall_tables


def calculate_tables(league_settings, schedule, matchup, scoreboards, box_scores, global_resources):
    leagues = league_settings['leagues'].split(',')
    leagues_names = []
    sports = league_settings['sports']
    
    overall_scores = defaultdict(list)
    tables = []
    for league_id in leagues:
        scores_pairs, _, _, league_name = scoreboards[league_id]
        leagues_names.append(league_name)
        scores = defaultdict(list)
        for matchup_results in scores_pairs[:matchup]:
            for p1, p2 in matchup_results:
                scores[p1[0]].append(p1[1])
                scores[p2[0]].append(p2[1])
        overall_scores.update(scores)

        scores_tables = _league_scores_tables(matchup, scores, scores_pairs, global_resources)

        plays = None
        plays_places = None
        plays_tables = []
        if league_settings['is_full_support']:
            plays_getters = {'basketball': utils.data.minutes, 'hockey': utils.data.player_games}
            plays = defaultdict(list)
            plays_places = defaultdict(list)
            for m in range(matchup):
                matchup_box_scores = box_scores[league_id][m]
                matchup_plays = plays_getters[sports](matchup_box_scores)
                if matchup_plays:
                    for team, value in matchup_plays.items():
                        plays[team].append(value)
                    matchup_places = utils.common.get_places(matchup_plays, True)
                    for team, value in matchup_places.items():
                        plays_places[team].append(value)

            plays_tables = _league_plays_tables(sports, matchup, scores, plays, plays_places, global_resources)
        
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        league_tables = scores_tables + plays_tables
        tables.append([league_name, link, league_tables])

    overall_tables = _export_overall_tables(len(leagues), matchup, overall_scores, global_resources)
    return {
        'results': {'leagues': tables, 'overall_tables': overall_tables}
    }

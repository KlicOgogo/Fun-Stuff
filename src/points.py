from collections import defaultdict, Counter

import numpy as np

import table.common
import table.points
import utils.common
import utils.data
import utils.points


def _export_league_tables(sports, matchup, scores, scores_pairs, plays, plays_places, n_last, titles, descriptions):
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

    if not plays:
        return tables

    table_key_dict = {'basketball': 'minutes', 'hockey': 'games'}
    table_key = table_key_dict[sports]
    tables.append([
        titles[table_key],descriptions[table_key],
        table.common.scores(plays, matchups, False, n_last)])
    tables.append([
        titles[f'{table_key}_places'], descriptions[f'{table_key}_places'],
        table.common.places(plays_places, matchups, False, False, n_last)])

    mean_scores = {}
    row_multiplier_dict = {'basketball': 100, 'hockey': 1}
    for team in scores:
        scores_row = np.array(scores[team])
        plays_row = np.array(plays[team])
        mean_scores[team] = list(np.round(scores_row / plays_row * row_multiplier_dict[sports], 2))
    tables.append([
        titles['mean'], descriptions['mean'],
        table.common.scores(mean_scores, matchups, False, n_last)])

    mean_scores_places = defaultdict(list)
    for m in range(matchup):
        matchup_data = {team: data[m] for team, data in mean_scores.items()}
        matchup_places = utils.common.get_places(matchup_data, True)
        for team, value in matchup_places.items():
            mean_scores_places[team].append(value)
    tables.append([
        titles['mean_places'], descriptions['mean_places'],
        table.common.places(mean_scores_places, matchups, False, False, n_last)])

    return tables


def _export_overall_tables(n_leagues, matchup, overall_scores, n_last, titles, descriptions):
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


def export_reports(league_settings, schedule, matchup, scoreboard_data, box_scores_data, global_resources):
    n_last = global_resources['config']['n_last_matchups']
    titles = global_resources['titles']
    descriptions = global_resources['descriptions']
    leagues = league_settings['leagues'].split(',')
    leagues_names = []
    sports = league_settings['sports']
    
    overall_scores = defaultdict(list)
    leagues_tables = []
    for league_id in leagues:
        scores_pairs, _, _, league_name = scoreboard_data[league_id]
        leagues_names.append(league_name)
        scores = defaultdict(list)
        for matchup_results in scores_pairs[:matchup]:
            for p1, p2 in matchup_results:
                scores[p1[0]].append(p1[1])
                scores[p2[0]].append(p2[1])
        overall_scores.update(scores)
    
        plays = None
        plays_places = None
        if league_settings['is_full_support']:
            plays_getters = {'basketball': utils.data.minutes, 'hockey': utils.data.player_games}
            plays = defaultdict(list)
            plays_places = defaultdict(list)
            for m in range(matchup):
                matchup_box_scores_data = box_scores_data[league_id][m]
                matchup_plays = plays_getters[sports](matchup_box_scores_data)
                if matchup_plays:
                    for team, value in matchup_plays.items():
                        plays[team].append(value)
                    matchup_places = utils.common.get_places(matchup_plays, True)
                    for team, value in matchup_places.items():
                        plays_places[team].append(value)
        
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        tables = _export_league_tables(
            sports, matchup, scores, scores_pairs, plays, plays_places, n_last, titles, descriptions)
        leagues_tables.append([league_name, link, tables])

    overall_tables = _export_overall_tables(len(leagues), matchup, overall_scores, n_last, titles, descriptions)
    global_config = global_resources['config']
    utils.common.save_tables(
        sports, leagues_tables, overall_tables, leagues[0], leagues_names[0],
        matchup, schedule, global_config, 'results')

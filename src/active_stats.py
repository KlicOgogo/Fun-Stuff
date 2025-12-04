from collections import defaultdict

import table.active_stats
import utils.active_stats


def _league_tables(sports, matchup, league_active_stats, descriptions):
    players_groups = ['skaters', 'goalies'] if sports == 'hockey' else ['players']

    data_by_team = defaultdict(lambda: defaultdict(list))
    categories_info = defaultdict(dict)
    for m in range(matchup):
        matchup_active_stats = league_active_stats[m]
        for team_key, team_matchup_active_stats in matchup_active_stats.items():
            team_name = team_key[0]
            categories_data, stats_data, _ = team_matchup_active_stats
            if not categories_data or not stats_data:
                continue
            for cat, stat, group in zip(categories_data, stats_data, players_groups):
                if not cat or not stat:
                    continue
                categories_info[team_name][group] = cat
                data_by_team[team_name][group].append(stat)

    tables = []
    for team_name in sorted(data_by_team):
        for group in data_by_team[team_name]:
            team_stats_list = data_by_team[team_name][group]

            team_stats_summarized = utils.active_stats.summarize_team_stats(team_stats_list, sports)
            team_categories = categories_info[team_name][group]
            if team_stats_summarized:
                tables.append([
                    f'{team_name}: {group}', descriptions['active_stats'],
                    table.active_stats.matchup(team_stats_summarized, team_categories)])

    return tables


def calculate_tables(league_settings, matchup, scoreboards, box_scores, descriptions):
    if not box_scores:
        return {}

    leagues = league_settings['leagues'].split(',')
    sports = league_settings['sports']

    leagues_tables = []
    for league_id in leagues:
        _, _, _, league_name = scoreboards[league_id]

        league_active_stats = box_scores[league_id]
        tables = _league_tables(sports, matchup, league_active_stats, descriptions)
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        leagues_tables.append([league_name, link, tables])

    return {
        'active stats': {'leagues': leagues_tables, 'overall_tables': []}
    }

import table.active_stats
import utils.active_stats


def _league_tables(sports, matchup, league_active_stats, descriptions):
    players_groups = ['skaters', 'goalies'] if sports == 'hockey' else ['players']
    data_by_team, categories_info = utils.active_stats.stats_by_team(matchup, league_active_stats, players_groups)

    tables = []
    for team_name in sorted(data_by_team):
        for group in data_by_team[team_name]:
            team_stats = data_by_team[team_name][group]

            team_player_totals = utils.active_stats.totals_by_players(team_stats, sports)
            team_categories = categories_info[team_name][group]
            if team_player_totals:
                tables.append([
                    f'{team_name}: {group}', descriptions['active_stats'],
                    table.active_stats.matchup(team_player_totals, team_categories)])

    return tables


def calculate_tables(group_settings, matchup, league_names, box_scores, descriptions):
    if not box_scores:
        return {}

    sports = group_settings['sports']
    leagues_tables = []
    for league_id in group_settings['leagues']:
        league_name = league_names[league_id]
        league_active_stats = box_scores[league_id]
        tables = _league_tables(sports, matchup, league_active_stats, descriptions)
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        leagues_tables.append([league_name, link, tables])

    return {
        'active stats': {'leagues': leagues_tables, 'overall_tables': []}
    }

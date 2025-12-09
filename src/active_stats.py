import table.active_stats
import utils.active_stats


def _league_tables(sports, matchups, league_box_scores, descriptions):
    data_by_team, categories_info = utils.active_stats.stats_by_team(matchups, league_box_scores, sports)

    tables = []
    for team_key in sorted(data_by_team):
        for group in data_by_team[team_key]:
            team_stats = data_by_team[team_key][group]

            team_categories = categories_info[team_key][group]
            _, category_short = team_categories
            team_player_totals = utils.active_stats.totals_by_players(team_stats, category_short, sports)
            if team_player_totals:
                team_name = team_key[0]
                tables.append([
                    f'{team_name}: {group}', descriptions['active_stats'],
                    table.active_stats.matchup(team_player_totals, team_categories)])

    return tables


def calculate_tables(group_settings, matchup, league_names, box_scores, descriptions):
    if not box_scores:
        return {}

    sports = group_settings['sports']
    leagues_tables = []
    matchups = range(1, matchup + 1)
    for league_id in group_settings['leagues']:
        league_name = league_names[league_id]
        league_box_scores = box_scores[league_id]
        tables = _league_tables(sports, matchups, league_box_scores, descriptions)
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        leagues_tables.append([league_name, link, tables])

    return {
        'active stats': {'leagues': leagues_tables, 'overall_tables': []}
    }

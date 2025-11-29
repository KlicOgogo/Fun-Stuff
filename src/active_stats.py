from collections import defaultdict

import table.active_stats
import utils.common
import utils.globals


_basketball_summarizable_cols = [
    'Minutes', 'Field Goals Made', 'Field Goals Attempted',
    'Free Throws Made', 'Free Throws Attempted', 'Three Pointers Made',
    'Rebounds', 'Assists', 'Steals', 'Blocks', 'Turnovers', 'Points',
]
_hockey_summarizable_cols = [
    # skaters
    'Skater Games Played', 'Goals', 'Assists', 'Points',
    'Plus/Minus', 'Penalty Minutes', 'Faceoffs Won',
    'Average Time on Ice',
    'Shots on Goal', 'Hits', 'Blocked Shots',
    'Special Teams Points',

    'Power Play Goals',
    'Power Play Assists',
    'Short Handed Goals',
    'Short Handed Assists',
    'Game-Winning Goals',

    'Shifts',
    'Hat Tricks',
    'Defensemen Points',

    # goalies
    'Games Started',
    'Wins',
    'Goals Against',
    'Saves',
    'Minutes Played',

    'Shutouts',
    'Overtime Losses',

    'FPTS',
]
_summarizable_cols = {
    'hockey': _hockey_summarizable_cols,
    'basketball': _basketball_summarizable_cols,
}


def _export_league_tables(sports, matchup, league_active_stats):
    players_groups = ['skaters', 'goalies'] if sports == 'hockey' else ['players']
    desc = utils.globals.descriptions()

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

            team_stats_summarized = _summarize(team_stats_list, sports)
            team_categories = categories_info[team_name][group]
            if team_stats_summarized:
                tables.append([f'{team_name}: {group}', desc['active_stats'],
                    table.active_stats.matchup(team_stats_summarized, team_categories)])
    
    return tables


def _get_updated_atoi(games1, atoi1, games2, atoi2):
    minutes1, seconds1 = list(map(int, atoi1.split(':')))
    minutes2, seconds2 = list(map(int, atoi2.split(':')))
    total_minutes = minutes1 * games1 + minutes2 * games2
    total_seconds = seconds1 * games1 + seconds2 * games2

    total_time = total_minutes * 60 + total_seconds
    average_time = int(total_time / (games1 + games2))
    average_minutes = average_time // 60
    average_seconds = average_time % 60
    seconds_formatted = str(average_seconds) if average_seconds > 9 else f'0{average_seconds}'
    return f'{average_minutes}:{seconds_formatted}'


def _summarize(stats_list, sports):
    stats_summarized = defaultdict(lambda: defaultdict(int))
    for stats_item in stats_list:
        for player, player_stats in stats_item.items():
            for cat, cat_value in player_stats.items():
                if cat == 'Skater Games Played':
                    if 'Average Time on Ice' in player_stats:
                        if stats_summarized[player]['Average Time on Ice'] == 0:
                            stats_summarized[player]['Average Time on Ice'] = '00:00'
                        stats_summarized[player]['Average Time on Ice'] = _get_updated_atoi(
                            stats_summarized[player][cat], stats_summarized[player]['Average Time on Ice'],
                            int(cat_value), player_stats['Average Time on Ice'])
                    stats_summarized[player][cat] += int(cat_value)
                elif cat == 'FPTS':
                    stats_summarized[player][cat] += float(cat_value)
                elif cat in _summarizable_cols[sports] and cat != 'Average Time on Ice':
                    stats_summarized[player][cat] += int(cat_value)

    return stats_summarized


def export_reports(league_settings, schedule, matchup, scoreboard_data, active_stats_data):
    leagues = league_settings['leagues'].split(',')
    leagues_names = []
    sports = league_settings['sports']
    
    leagues_tables = []
    for league_id in leagues:
        _, _, _, league_name = scoreboard_data[league_id]
        leagues_names.append(league_name)

        league_active_stats = active_stats_data[league_id]
        tables = _export_league_tables(sports, matchup, league_active_stats)
        link = f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}'
        leagues_tables.append([league_name, link, tables])

    utils.common.save_tables(
        sports, leagues_tables, [], leagues[0], leagues_names[0], matchup, schedule, 'active_stats')

from collections import defaultdict


_ATOI = 'Average Time on Ice'
_basketball_summarizable_cols = [
    'Minutes',
    'Field Goals Made', 'Field Goals Attempted',
    'Free Throws Made', 'Free Throws Attempted',
    'Three Pointers Made',
    'Rebounds',
    'Assists',
    'Steals',
    'Blocks',
    'Turnovers',
    'Points',
]
_hockey_summarizable_cols = [
    # skaters
    'Skater Games Played',
    'Goals', 'Assists', 'Points',
    'Plus/Minus',
    'Penalty Minutes',
    'Faceoffs Won',
    'Shots on Goal',
    'Hits',
    'Blocked Shots',
    'Special Teams Points',

    'Power Play Goals', 'Power Play Assists',
    'Short Handed Goals', 'Short Handed Assists',
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
]
_int_summarizable_cols = {
    'hockey': _hockey_summarizable_cols,
    'basketball': _basketball_summarizable_cols,
}


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


def _add_to_category_stats(cat, cat_value, stats_summarized, player_stats, sports):
    if cat == 'Skater Games Played' and _ATOI in player_stats:
        stats_summarized.setdefault(_ATOI, '00:00')
        stats_summarized[_ATOI] = _get_updated_atoi(
            stats_summarized[cat], stats_summarized[_ATOI],
            int(cat_value), player_stats[_ATOI])

    if cat in _int_summarizable_cols[sports]:
        stats_summarized[cat] += int(cat_value)
    elif cat == 'FPTS':
        stats_summarized[cat] += float(cat_value)


def totals_by_players(stats_list, sports):
    stats_summarized = defaultdict(lambda: defaultdict(int))
    for stats_item in stats_list:
        for player, player_stats in stats_item.items():
            for cat, cat_value in player_stats.items():
                _add_to_category_stats(cat, cat_value, stats_summarized[player], player_stats, sports)

    return stats_summarized


def stats_by_team(matchup, league_active_stats, players_groups):
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

    return data_by_team, categories_info


def totals_by_team(stats_list, sports):
    team_totals = defaultdict(int)
    for stats_item in stats_list:
        for player_stats in stats_item.values():
            for cat, cat_value in player_stats.items():
                _add_to_category_stats(cat, cat_value, team_totals, player_stats, sports)

    return team_totals

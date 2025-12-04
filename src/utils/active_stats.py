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


def summarize_team_stats(stats_list, sports):
    stats_summarized = defaultdict(lambda: defaultdict(int))
    for stats_item in stats_list:
        for player, player_stats in stats_item.items():
            for cat, cat_value in player_stats.items():
                if cat == 'Skater Games Played' and _ATOI in player_stats:
                    stats_summarized[player].setdefault(_ATOI, '00:00')
                    stats_summarized[player][_ATOI] = _get_updated_atoi(
                        stats_summarized[player][cat], stats_summarized[player][_ATOI],
                        int(cat_value), player_stats[_ATOI])

                if cat in _int_summarizable_cols[sports]:
                    stats_summarized[player][cat] += int(cat_value)
                elif cat == 'FPTS':
                    stats_summarized[player][cat] += float(cat_value)

    return stats_summarized
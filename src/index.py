from collections import defaultdict
import itertools
import json
from multiprocessing.dummy import Pool as ThreadPool
from operator import itemgetter
import os
import sys
import traceback

import active_stats
import categories
import points
import utils.common
import utils.data
import utils.globals


def _process_leagues(leagues, sports_list, browser):
    functions_by_type = {'points': points.export_reports, 'categories': categories.export_reports}
    for league_settings, type_item, _ in leagues:
        sports = league_settings['sports']
        if sports not in sports_list:
            continue

        schedule = None
        use_offline_schedule = utils.globals.config()['use_offline_schedule']
        for league in league_settings['leagues'].split(','):
            current_schedule = utils.data.schedule(
                league, sports, league_settings['is_playoffs_support'], use_offline_schedule, browser)
            if schedule is None:
                schedule = current_schedule
            elif schedule != current_schedule:
                schedule = None
                break

        if schedule is None:
            continue

        matchup, is_season_ended = utils.common.find_proper_matchup(schedule)
        if matchup == -1:
            continue

        is_full_support = league_settings['is_full_support']
        use_offline_data = utils.globals.config()['use_offline_data']
        online_page_matchups = []
        if is_full_support and not use_offline_data:
            if is_season_ended:
                online_page_matchups = [matchup]
            else:
                online_range_left = max(1, matchup - utils.globals.config()['refresh_matchups'])
                online_page_matchups = list(range(online_range_left, matchup + 1))

        scoreboard_data = {}
        for league in league_settings['leagues'].split(','):
            scoreboard_data[league] = utils.data.scoreboard(
                league, sports, matchup, browser, online_page_matchups, type_item == 'categories')
        
        matchups_to_process = [matchup]
        if is_full_support:
            process_range_left = max(1, matchup - utils.globals.config()['refresh_matchups'])
            matchups_to_process = list(range(process_range_left, matchup + 1))

        box_scores_data = None
        if league_settings['is_full_support']:
            box_scores_data = defaultdict(list)
            for league in league_settings['leagues'].split(','):
                pairs, team_names, _ = scoreboard_data[league]
                for m in range(matchup):
                    current_matchup = m + 1
                    is_offline = current_matchup not in online_page_matchups or use_offline_data
                    matchup_data = utils.data.box_scores(
                        league, team_names, sports, current_matchup, pairs[m], schedule, is_offline, browser)
                    box_scores_data[league].append(matchup_data)
        
        if box_scores_data:
            for m in matchups_to_process:
                active_stats.export_reports(league_settings, schedule, m, box_scores_data)
        
        export_reports_function = functions_by_type[type_item]
        for m in matchups_to_process:
            export_reports_function(league_settings, schedule, m, scoreboard_data, box_scores_data)


def _split_for_parallel(index_config, league_types, league_sizes, count):
    result_indexes = [[] for _ in range(count)]
    result_lengths = [0 for _ in range(count)]

    settings_grouped = [
        (league_settings, league_type, league_size)
        for league_settings, league_type, league_size in zip(index_config, league_types, league_sizes)
    ]
    for single_settings in sorted(settings_grouped, reverse=True, key=itemgetter(2)):
        lengths_with_sizes = [(length, -len(index)) for length, index in zip(result_lengths, result_indexes)]
        min_value = min(lengths_with_sizes)
        settings_position = lengths_with_sizes.index(min_value)
        result_lengths[settings_position] += single_settings[2]
        result_indexes[settings_position].append(single_settings)
    
    return result_indexes


def main():
    sports_list = ['basketball', 'hockey']
    types_list = ['categories', 'points']
    for arg in sys.argv[1:]:
        if arg in types_list:
            types_list = [arg]
        if arg in sports_list:
            sports_list = [arg]

    index_config = []
    index_types = []
    index_sizes = []
    leagues_settings = {}
    for type_item in types_list:
        leagues_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', f'res/{type_item}.json')
        with open(leagues_path, 'r', encoding='utf-8') as fp:
            leagues = json.load(fp)
            leagues_settings[type_item] = leagues
            index_config.extend(leagues)
            index_types.extend([type_item] * len(leagues))
            index_sizes.extend([l['leagues'].count(',') + 1 for l in leagues])

    n_jobs = utils.globals.config()['n_jobs']
    sleep_timeout = utils.globals.config()['timeout']
    settings_splitted = _split_for_parallel(index_config, index_types, index_sizes, n_jobs)

    if n_jobs == 1:
        _process_leagues(settings_splitted[0], sports_list, utils.data.BrowserManager(40, sleep_timeout))
    else:
        pool = ThreadPool(n_jobs)
        process_params = zip(
            settings_splitted,
            itertools.repeat(sports_list),
            [utils.data.BrowserManager(40, sleep_timeout) for _ in range(n_jobs)]
        )
        pool.starmap(_process_leagues, process_params)
        pool.close()
        pool.join()

    utils.common.save_index(index_config, is_archive=True)
    utils.common.save_index(index_config, is_archive=False)
    utils.common.save_reports_type_indexes()

if __name__ == '__main__':
    try:
        utils.globals.init_globals()
        main()
    except Exception as e:
        traceback.print_exc()
    finally:
        utils.globals.save_league_names()

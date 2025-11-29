from collections import defaultdict
import itertools
import json
from multiprocessing.dummy import Pool as ThreadPool
from operator import itemgetter
import os
import random
import sys
import traceback

import active_stats
import categories
import points
import utils.common
import utils.data
import utils.globals


def _process_leagues(leagues, sports_list, old_data_loaded_matchups, browser):
    config = utils.globals.config()
    league_names = defaultdict(dict)
    data_loaded_matchups = defaultdict(dict)

    try:
        functions_by_type = {'points': points.export_reports, 'categories': categories.export_reports}
        for league_settings, type_item, _ in leagues:
            sports = league_settings['sports']
            if sports not in sports_list:
                continue

            schedule = None
            use_offline_schedule = config['use_offline_schedule']
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
            main_league = league_settings['leagues'].split(',')[0]
            league_loaded_matchups = old_data_loaded_matchups[sports].get(main_league, [])
            matchup_str = str(matchup)
            is_data_loaded = matchup_str in league_loaded_matchups
            use_offline_data = config['use_offline_data'] or is_data_loaded
            online_page_matchups = []
            if is_full_support and not use_offline_data:
                if is_season_ended:
                    online_page_matchups = [matchup]
                else:
                    online_range_left = max(1, matchup - config['refresh_matchups'])
                    online_page_matchups = list(range(online_range_left, matchup + 1))

            scoreboard_data = {}
            for league in league_settings['leagues'].split(','):
                scoreboard_data[league] = utils.data.scoreboard(
                    league, sports, matchup, browser, online_page_matchups, type_item == 'categories')
                league_names[sports][league] = scoreboard_data[league][3]
            
            matchups_to_process = [matchup]
            if is_full_support:
                process_range_left = max(1, matchup - config['refresh_matchups'])
                matchups_to_process = list(range(process_range_left, matchup + 1))

            box_scores_data = None
            if league_settings['is_full_support']:
                box_scores_data = defaultdict(list)
                for league in league_settings['leagues'].split(','):
                    pairs, team_names, _, league_name = scoreboard_data[league]
                    for m in range(matchup):
                        current_matchup = m + 1
                        is_offline = current_matchup not in online_page_matchups or use_offline_data
                        matchup_data = utils.data.box_scores(
                            league, league_name, team_names, sports,
                            current_matchup, pairs[m], schedule, is_offline, browser)
                        box_scores_data[league].append(matchup_data)
            
            if box_scores_data:
                for m in matchups_to_process:
                    active_stats.export_reports(league_settings, schedule, m, scoreboard_data, box_scores_data)
            
            export_reports_function = functions_by_type[type_item]
            for m in matchups_to_process:
                export_reports_function(
                    league_settings, schedule, m, scoreboard_data, box_scores_data, config['n_last_matchups'])
            
            data_loaded_matchups[sports][main_league] = league_loaded_matchups
            if not is_data_loaded:
                data_loaded_matchups[sports][main_league].append(matchup_str)
        
        return {
            'league_names': league_names,
            'data_loaded_matchups': data_loaded_matchups,
        }
    except Exception as e:
        return {
            'league_names': league_names,
            'data_loaded_matchups': data_loaded_matchups,
            'error': e,
        }


def _split_for_parallel(index_config, league_types, league_sizes, count):
    result_indexes = [[] for _ in range(count)]
    result_lengths = [0 for _ in range(count)]

    settings_grouped = [
        (league_settings, league_type, league_size)
        for league_settings, league_type, league_size in zip(index_config, league_types, league_sizes)
    ]
    random.shuffle(settings_grouped)
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

    data_loaded_matchups = utils.globals.data_loaded_matchups()
    league_names = utils.globals.league_names()

    if n_jobs == 1:
        names_and_matchups = _process_leagues(
            settings_splitted[0], sports_list, data_loaded_matchups, utils.data.BrowserManager(50, sleep_timeout))
        for sports in sports_list:
            league_names[sports].update(names_and_matchups['league_names'][sports])
            data_loaded_matchups[sports].update(names_and_matchups['data_loaded_matchups'][sports])
        
        utils.globals.save_data_loaded_matchups()
        utils.globals.save_league_names()
        
        if 'error' in names_and_matchups:
            raise names_and_matchups[e]
    else:
        pool = ThreadPool(n_jobs)
        process_params = zip(
            settings_splitted,
            itertools.repeat(sports_list),
            itertools.repeat(data_loaded_matchups),
            [utils.data.BrowserManager(50, sleep_timeout) for _ in range(n_jobs)]
        )
        names_and_matchups_list = pool.starmap(_process_leagues, process_params)
        pool.close()
        pool.join()
        error = None
        for names_and_matchups in names_and_matchups_list:
            for sports in sports_list:
                league_names[sports].update(names_and_matchups['league_names'][sports])
                data_loaded_matchups[sports].update(names_and_matchups['data_loaded_matchups'][sports])
                if 'error' in names_and_matchups:
                    error = names_and_matchups['error']

        utils.globals.save_data_loaded_matchups()
        utils.globals.save_league_names()

        if error is not None:
            raise error

    utils.common.save_index(utils.globals.REPORT_TYPES, index_config, league_names, is_archive=True)
    utils.common.save_index(utils.globals.REPORT_TYPES, index_config, league_names, is_archive=False)
    utils.common.save_reports_type_indexes(utils.globals.REPORT_TYPES, league_names)

if __name__ == '__main__':
    try:
        utils.globals.init_globals()
        main()
    except Exception as e:
        traceback.print_exc()

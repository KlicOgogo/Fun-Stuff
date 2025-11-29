from collections import defaultdict
from copy import deepcopy
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
from utils.json_utils import dump as json_dump
from utils.json_utils import load as json_load


_repo_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def _process_leagues(global_res, leagues, sports_list, old_data_loaded_matchups, browser):
    global_config = global_res['config']
    league_names = defaultdict(dict)
    data_loaded_matchups = defaultdict(dict)

    try:
        functions_by_type = {'points': points.export_reports, 'categories': categories.export_reports}
        for league_settings, type_item, _ in leagues:
            sports = league_settings['sports']
            if sports not in sports_list:
                continue

            schedule = None
            use_offline_schedule = global_config['use_offline_schedule']
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
            use_offline_data = global_config['use_offline_data'] or is_data_loaded
            online_page_matchups = []
            if is_full_support and not use_offline_data:
                if is_season_ended:
                    online_page_matchups = [matchup]
                else:
                    online_range_left = max(1, matchup - global_config['refresh_matchups'])
                    online_page_matchups = list(range(online_range_left, matchup + 1))

            scoreboard_data = {}
            for league in league_settings['leagues'].split(','):
                scoreboard_data[league] = utils.data.scoreboard(
                    league, sports, matchup, browser, online_page_matchups, type_item == 'categories')
                league_names[sports][league] = scoreboard_data[league][3]
            
            matchups_to_process = [matchup]
            if is_full_support:
                process_range_left = max(1, matchup - global_config['refresh_matchups'])
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
                    active_stats.export_reports(
                        league_settings, schedule, m, scoreboard_data, box_scores_data, global_res)
            
            export_reports_function = functions_by_type[type_item]
            for m in matchups_to_process:
                export_reports_function(
                    league_settings, schedule, m, scoreboard_data, box_scores_data, global_res)
            
            data_loaded_matchups[sports][main_league] = league_loaded_matchups
            if not is_data_loaded:
                data_loaded_matchups[sports][main_league].append(matchup_str)

            utils.common.save_league_index(league_names[sports][main_league], league_settings, global_config)

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


def _split_for_parallel(leagues_to_process, league_types, league_sizes, count):
    result_indexes = [[] for _ in range(count)]
    result_lengths = [0 for _ in range(count)]

    settings_grouped = [
        (league_settings, league_type, league_size)
        for league_settings, league_type, league_size in zip(leagues_to_process, league_types, league_sizes)
    ]
    random.shuffle(settings_grouped)
    for single_settings in sorted(settings_grouped, reverse=True, key=itemgetter(2)):
        lengths_with_sizes = [(length, -len(index)) for length, index in zip(result_lengths, result_indexes)]
        min_value = min(lengths_with_sizes)
        settings_position = lengths_with_sizes.index(min_value)
        result_lengths[settings_position] += single_settings[2]
        result_indexes[settings_position].append(single_settings)
    
    return result_indexes


def main(global_res):
    global_config = global_res['config']
    sports_list = ['basketball', 'hockey']
    types_to_process = all_types = ['categories', 'points']
    for arg in sys.argv[1:]:
        if arg in types_to_process:
            types_to_process = [arg]
        if arg in sports_list:
            sports_list = [arg]

    leagues_to_process = []
    index_types = []
    index_sizes = []
    leagues_settings = []
    for type_item in all_types:
        leagues_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', f'res/{type_item}.json')
        leagues = json_load(leagues_path)
        leagues_settings.extend(leagues)
        if type_item in types_to_process:
            leagues_to_process.extend(leagues)
            index_types.extend([type_item] * len(leagues))
            index_sizes.extend([l['leagues'].count(',') + 1 for l in leagues])

    n_jobs = global_config['n_jobs']
    sleep_timeout = global_config['timeout']
    settings_splitted = _split_for_parallel(leagues_to_process, index_types, index_sizes, n_jobs)

    league_names_path = os.path.join(_repo_root_dir, 'res/league_names.json')
    league_names = json_load(league_names_path, defaultdict(dict))

    data_loaded_matchups_path = os.path.join(_repo_root_dir, 'res/data_loaded_matchups.config')
    data_loaded_matchups = json_load(data_loaded_matchups_path, defaultdict(dict))

    if n_jobs == 1:
        names_and_matchups = _process_leagues(
            global_res, settings_splitted[0], sports_list,
            data_loaded_matchups, utils.data.BrowserManager(50, sleep_timeout))
        for sports in sports_list:
            league_names[sports].update(names_and_matchups['league_names'][sports])
            data_loaded_matchups[sports].update(names_and_matchups['data_loaded_matchups'][sports])
        
        json_dump(league_names, league_names_path)
        json_dump(data_loaded_matchups, data_loaded_matchups_path)

        if 'error' in names_and_matchups:
            raise names_and_matchups[e]
    else:
        pool = ThreadPool(n_jobs)
        process_params = [
            (
                deepcopy(global_res),
                job_settings,
                deepcopy(sports_list),
                deepcopy(data_loaded_matchups),
                utils.data.BrowserManager(50, sleep_timeout)
            )
            for job_settings in settings_splitted
        ]
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

        json_dump(league_names, league_names_path)
        json_dump(data_loaded_matchups, data_loaded_matchups_path)

        if error is not None:
            raise error

    report_types = global_config['report_types']
    utils.common.save_homepage(report_types, global_config, leagues_settings, league_names)
    utils.common.save_archive(report_types, global_config, league_names)
    utils.common.save_reports_type_indexes(report_types, global_config, league_names)

if __name__ == '__main__':
    try:
        global_res = utils.common.load_global_resources()
        main(global_res)
    except Exception as e:
        traceback.print_exc()

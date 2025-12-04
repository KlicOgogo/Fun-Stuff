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
_all_types = ['categories', 'points']
_tables_calculators = {'points': points.calculate_tables, 'categories': categories.calculate_tables}


def _process_group(group_settings, schedule, scoring_type, browser, global_resources, online_matchups, matchups):
    global_config = global_resources['config']
    sports = group_settings['sports']
    scoreboards = {}
    league_names = {}
    current_matchup = max(matchups)
    for league in group_settings['leagues'].split(','):
        scoreboards[league] = utils.data.scoreboards(
            league, sports, current_matchup, browser, online_matchups, scoring_type == 'categories')
        league_names[league] = scoreboards[league][3]

    main_league = group_settings['leagues'].split(',')[0]
    main_league_name = league_names[main_league]

    box_scores = utils.data.group_box_scores(
        group_settings, schedule, current_matchup, browser, scoreboards, online_matchups)

    tables_calculator = _tables_calculators[scoring_type]
    for matchup in matchups:
        tables = tables_calculator(group_settings, schedule, matchup, scoreboards, box_scores, global_resources)

        active_stats_tables = active_stats.calculate_tables(
            group_settings, matchup, scoreboards, box_scores, global_resources['descriptions'])
        tables.update(active_stats_tables)

        for report_type, type_tables in tables.items():
            title = f'{main_league_name} ({sports}). Matchup {matchup} {report_type}'
            template_params = {'title': title}
            template_params.update(type_tables)
            utils.common.save_tables(group_settings, matchup, schedule, global_config, report_type, template_params)

    utils.common.save_league_index(main_league_name, group_settings, global_config)
    return league_names


def _process_league_groups(global_resources, leagues, sports_to_process, data_loaded_matchups, browser):
    result = {
        'league_names': defaultdict(dict),
        'data_loaded_matchups': defaultdict(dict),
    }
    try:
        for group_settings, scoring_type, _ in leagues:
            if group_settings['sports'] not in sports_to_process:
                continue

            global_config = global_resources['config']
            schedule = utils.data.group_schedule(group_settings, browser, global_config['use_offline_schedule'])
            if schedule is None:
                continue

            matchup, is_season_ended = utils.common.find_proper_matchup(schedule)
            if matchup == -1:
                continue

            main_league = group_settings['leagues'].split(',')[0]
            sports = group_settings['sports']
            group_loaded_matchups = data_loaded_matchups[sports].get(main_league, [])
            matchup_str = str(matchup)
            is_data_loaded = matchup_str in group_loaded_matchups
            is_full_support = group_settings['is_full_support']

            refresh_range_left = max(1, matchup - global_config['refresh_matchups'])
            refresh_range = list(range(refresh_range_left, matchup + 1))
            online_matchups = []
            if is_full_support and not is_data_loaded:
                online_matchups = [matchup] if is_season_ended else refresh_range
            process_matchups = refresh_range if is_full_support else [matchup] 

            league_names = _process_group(
                group_settings, schedule, scoring_type, browser, global_resources, online_matchups, process_matchups)

            result['league_names'][sports].update(league_names)
            result['data_loaded_matchups'][sports][main_league] = list(set(group_loaded_matchups + [matchup_str]))

    except Exception as e:
        result.update({'error': e})
    finally:
        return result


def _parse_arguments():
    sports_to_process = ['basketball', 'hockey']
    types_to_process = _all_types
    for arg in sys.argv[1:]:
        if arg in types_to_process:
            types_to_process = [arg]
        if arg in sports_to_process:
            sports_to_process = [arg]
    return sports_to_process, types_to_process


def _split_leagues_to_jobs(types_to_process, n_jobs):
    leagues_to_process = []
    index_types = []
    index_sizes = []
    leagues_settings = []
    for scoring_type in _all_types:
        leagues_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', f'res/{scoring_type}.json')
        leagues = json_load(leagues_path)
        leagues_settings.extend(leagues)
        if scoring_type in types_to_process:
            leagues_to_process.extend(leagues)
            index_types.extend([scoring_type] * len(leagues))
            index_sizes.extend([l['leagues'].count(',') + 1 for l in leagues])

    result_indexes = [[] for _ in range(n_jobs)]
    result_lengths = [0 for _ in range(n_jobs)]

    settings_grouped = [
        (group_settings, league_type, league_size)
        for group_settings, league_type, league_size in zip(leagues_to_process, index_types, index_sizes)
    ]
    random.shuffle(settings_grouped)
    for single_settings in sorted(settings_grouped, reverse=True, key=itemgetter(2)):
        lengths_with_sizes = [(length, -len(index)) for length, index in zip(result_lengths, result_indexes)]
        min_value = min(lengths_with_sizes)
        settings_position = lengths_with_sizes.index(min_value)
        result_lengths[settings_position] += single_settings[2]
        result_indexes[settings_position].append(single_settings)
    
    return result_indexes, leagues_settings


def main(global_resources):
    sports_to_process, types_to_process = _parse_arguments()
    global_config = global_resources['config']
    n_jobs = global_config['n_jobs']
    settings_splitted, leagues_settings = _split_leagues_to_jobs(types_to_process, n_jobs)

    data_loaded_matchups_path = os.path.join(_repo_root_dir, 'res/data_loaded_matchups.config')
    data_loaded_matchups = json_load(data_loaded_matchups_path, defaultdict(dict))
    sleep_timeout = global_config['timeout']
    if n_jobs == 1:
        names_and_matchups = _process_league_groups(
            global_resources, settings_splitted[0], sports_to_process,
            data_loaded_matchups, utils.data.BrowserManager(50, sleep_timeout))
        names_and_matchups_list = [names_and_matchups]
    else:
        pool = ThreadPool(n_jobs)
        process_params = [
            (
                deepcopy(global_resources),
                job_settings,
                deepcopy(sports_to_process),
                deepcopy(data_loaded_matchups),
                utils.data.BrowserManager(50, sleep_timeout)
            )
            for job_settings in settings_splitted
        ]
        names_and_matchups_list = pool.starmap(_process_league_groups, process_params)
        pool.close()
        pool.join()

    error = None
    league_names_path = os.path.join(_repo_root_dir, 'res/league_names.json')
    league_names = json_load(league_names_path, defaultdict(dict))
    for names_and_matchups in names_and_matchups_list:
        for sports in sports_to_process:
            league_names[sports].update(names_and_matchups['league_names'][sports])
            data_loaded_matchups[sports].update(names_and_matchups['data_loaded_matchups'][sports])

            if 'error' in names_and_matchups:
                error = names_and_matchups['error']

    json_dump(league_names, league_names_path)
    json_dump(data_loaded_matchups, data_loaded_matchups_path)

    if error is not None:
        raise error

    utils.common.save_homepage(global_config, leagues_settings, league_names)
    utils.common.save_archive(global_config, league_names)
    utils.common.save_report_type_indexes(global_config, league_names)


if __name__ == '__main__':
    try:
        global_resources = utils.common.load_global_resources()
        main(global_resources)
    except Exception as e:
        traceback.print_exc()

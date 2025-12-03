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
_functions_by_type = {'points': points.calculate_tables, 'categories': categories.calculate_tables}


def _process_group(group_settings, scoring_type, sports_to_process, old_data_loaded_matchups,
                   browser, global_resources, league_names, data_loaded_matchups):
    global_config = global_resources['config']
    sports = group_settings['sports']
    if sports not in sports_to_process:
        return

    schedule = None
    use_offline_schedule = global_config['use_offline_schedule']
    for league in group_settings['leagues'].split(','):
        current_schedule = utils.data.schedule(
            league, sports, group_settings['is_playoffs_support'], use_offline_schedule, browser)
        if schedule is None:
            schedule = current_schedule
        elif schedule != current_schedule:
            schedule = None
            break

    if schedule is None:
        return

    matchup, is_season_ended = utils.common.find_proper_matchup(schedule)
    if matchup == -1:
        return

    is_full_support = group_settings['is_full_support']
    main_league = group_settings['leagues'].split(',')[0]
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
    for league in group_settings['leagues'].split(','):
        scoreboard_data[league] = utils.data.scoreboard(
            league, sports, matchup, browser, online_page_matchups, scoring_type == 'categories')
        league_names[sports][league] = scoreboard_data[league][3]
    main_league_name = league_names[sports][main_league]

    matchups_to_process = [matchup]
    if is_full_support:
        process_range_left = max(1, matchup - global_config['refresh_matchups'])
        matchups_to_process = list(range(process_range_left, matchup + 1))

    box_scores = None
    if group_settings['is_full_support']:
        box_scores = defaultdict(list)
        for league in group_settings['leagues'].split(','):
            pairs, team_names, _, league_name = scoreboard_data[league]
            for m in range(matchup):
                current_matchup = m + 1
                is_offline = current_matchup not in online_page_matchups or use_offline_data
                matchup_box_scores = None
                if is_offline:
                    matchup_box_scores = utils.data.box_scores_offline(
                        league, league_name, team_names, sports, current_matchup)
                if matchup_box_scores is None:
                    matchup_box_scores = utils.data.box_scores_online(
                        league, sports, current_matchup, pairs[m], schedule, browser)
                box_scores[league].append(matchup_box_scores)

    calculate_tables_function = _functions_by_type[scoring_type]
    for m in matchups_to_process:
        tables = calculate_tables_function(
            group_settings, schedule, m, scoreboard_data, box_scores, global_resources)

        if box_scores:
            active_stats_tables = active_stats.calculate_tables(
                group_settings, m, scoreboard_data, box_scores, global_resources['descriptions'])
            tables.update(active_stats_tables)

        for report_type, type_tables in tables.items():
            title = f'{main_league_name} ({sports}). Matchup {m} {report_type}'
            template_params = {'title': title}
            template_params.update(type_tables)
            utils.common.save_tables(
                sports, main_league, m, schedule, global_config, report_type, template_params)

    data_loaded_matchups[sports][main_league] = league_loaded_matchups
    if not is_data_loaded:
        data_loaded_matchups[sports][main_league].append(matchup_str)

    utils.common.save_league_index(main_league_name, group_settings, global_config)


def _process_league_groups(global_resources, leagues, sports_to_process, old_data_loaded_matchups, browser):
    result = {
        'league_names': defaultdict(dict),
        'data_loaded_matchups': defaultdict(dict),
    }
    try:
        for group_settings, scoring_type, _ in leagues:
            _process_group(group_settings, scoring_type, sports_to_process, old_data_loaded_matchups,
                           browser, global_resources, result['league_names'], result['data_loaded_matchups'])
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
    global_config = global_resources['config']

    sports_to_process, types_to_process = _parse_arguments()
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

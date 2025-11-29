from collections import defaultdict
import datetime
from operator import itemgetter
import os
from pathlib import Path
import re

from jinja2 import Template
import numpy as np

from utils.json_utils import load as json_load


_repo_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
_sports_keys = ['basketball', 'hockey']
_sports_to_display = {
    'hockey': 'NHL',
    'basketball': 'NBA',
}
_global_resources_keys = ['category_names', 'config', 'descriptions', 'titles']


def load_global_resources():
    global_resources = {}
    for key in _global_resources_keys:
        resources_path = os.path.join(_repo_root_dir, 'res', f'{key}.json')
        resources = json_load(resources_path)
        global_resources[key] = resources
    return global_resources


def find_proper_matchup(schedule):
    today = datetime.datetime.today().date()
    # today = datetime.date(2025, 11, 24)
    four_days_ago = today - datetime.timedelta(days=4)
    eleven_days_ago = four_days_ago - datetime.timedelta(days=7)
    for index, matchup_number in enumerate(sorted(schedule)):
        matchup_date = schedule[matchup_number][0]
        if today > matchup_date[1]:
            if matchup_date[0] <= four_days_ago <= matchup_date[1]:
                return matchup_number, False
            elif index == len(schedule) - 1 and matchup_date[0] <= eleven_days_ago <= matchup_date[1]:
                return matchup_number, True
    return -1, False


def _save_html(template_name, template_params, html_path):
    template_path = os.path.join(_repo_root_dir, 'templates', f'{template_name}.html')
    with open(template_path, 'r', encoding='utf-8') as template_fp:
        template = Template(template_fp.read())
    html_str = template.render(template_params)
    with open(html_path, 'w', encoding='utf-8') as html_fp:
        html_fp.write(html_str)


def _get_previous_reports_data(index_relative_path, matchup, schedule, github):
    report_dir = os.path.join(_repo_root_dir, '..', index_relative_path)
    contents = [path for path in os.listdir(report_dir)] if os.path.isdir(report_dir) else []
    html_list = [path for path in contents if os.path.splitext(path)[1] == '.html']
    reports = [html for html in html_list if re.match(r'matchup_\d+\.html', html)]
    matchup_list = [int(re.findall(r'matchup_(\d+)\.html', r)[0]) for r in reports]
    prev_reports = [m for m in matchup_list if m < matchup]
    
    previous_reports_data = {}
    for m in prev_reports:
        report_link = f'https://{github}.github.io/{index_relative_path}/matchup_{m}.html'
        this_matchup_begin, this_matchup_end = map(lambda x: x.strftime('%d/%m/%Y'), schedule[m][0])
        report_text = f'Matchup {m} ({this_matchup_begin} - {this_matchup_end}).'
        previous_reports_data[m] = (report_text, report_link)
    return previous_reports_data


def _get_season_reports(season_relative_path, github):
    reports_dir = os.path.join(_repo_root_dir, '..', season_relative_path)
    matchups = []
    for item in os.listdir(reports_dir):
        found = re.findall(r'matchup_(\d+)\.html', item)
        if len(found) == 1 and os.path.isfile(os.path.join(reports_dir, item)):
            matchups.append(int(found[0]))
    
    season_reports = {}
    latest_report_url = None
    for m in sorted(matchups, reverse=True):
        link = f'https://{github}.github.io/{season_relative_path}/matchup_{m}.html'
        season_reports[f'Matchup {m}'] = link
        if latest_report_url is None:
            latest_report_url = link
    return season_reports, latest_report_url


def get_opponent_dict(scores_pairs):
    opp_dict = {}
    for p1, p2 in scores_pairs:
        opp_dict[p1[0]] = p2[0]
        opp_dict[p2[0]] = p1[0]
    return opp_dict


def get_places(scores_dict, reverse):
    sorted_scores = sorted(scores_dict.items(), key=itemgetter(1), reverse=reverse)
    only_scores_array = np.array(list(map(itemgetter(1), sorted_scores)))
    places = {}
    for team, score in sorted_scores:
        score_indexes = np.where(only_scores_array == score)
        places[team] = 1 + np.mean(score_indexes)
    return places

def save_archive(report_types, global_config, league_names):
    sports_indexes = defaultdict(lambda: defaultdict(list))
    for sports in _sports_keys:
        for report_type in report_types:
            github = global_config[report_type]['github']
            reports_repo_name = global_config[report_type]['repo_name']
            reports_dir_name = global_config[report_type]['dir_name']
            reports_dir = os.path.join(_repo_root_dir, '..', reports_repo_name, reports_dir_name)
            index_url_prefix = f'https://{github}.github.io/{reports_repo_name}/{reports_dir_name}/{sports}'
            sports_reports_dir = os.path.join(reports_dir, sports)
            if not os.path.isdir(sports_reports_dir):
                continue
            for league_id in os.listdir(sports_reports_dir):
                if not os.path.isdir(os.path.join(sports_reports_dir, league_id)):
                    continue
                league_name = league_names[sports][league_id]
                league_link = f'{index_url_prefix}/{league_id}/index.html'
                reports_type_name = report_type.capitalize()
                sports_display = _sports_to_display[sports]
                sports_indexes[sports_display][league_name].append([reports_type_name, league_link])

    template_params = {
        'title': 'Fantasy Fun Stuff (archive)',
        'indexes': sports_indexes,
        'archive_url': None,
    }
    repo = global_config['main_repo']
    archive_path = os.path.join(_repo_root_dir, '..', repo, 'archive.html')
    _save_html('index', template_params, archive_path)


def save_homepage(report_types, global_config, index_config, league_names):
    sports_indexes = defaultdict(lambda: defaultdict(list))
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'

    for league_settings in index_config:
        league_id = league_settings['leagues'].split(',')[0]
        sports = league_settings['sports']

        for report_type in report_types:
            github = global_config[report_type]['github']
            reports_repo_name = global_config[report_type]['repo_name']
            reports_dir_name = global_config[report_type]['dir_name']

            season_relative_path = os.path.join(reports_repo_name, reports_dir_name, sports, league_id, season_str)
            reports_dir = os.path.join(_repo_root_dir, '..', season_relative_path)
            if not os.path.isdir(reports_dir):
                continue
            _, latest_report_link = _get_season_reports(season_relative_path, github)

            league_name = league_names[sports][league_id]
            reports_type_name = report_type.capitalize()
            sports_display = _sports_to_display[sports]
            sports_indexes[sports_display][league_name].append([reports_type_name, latest_report_link])

    github = global_config['main_github']
    repo = global_config['main_repo']
    template_params = {
        'title': 'Fantasy Fun Stuff',
        'indexes': sports_indexes,
        'archive_url': f'https://{github}.github.io/{repo}/archive.html',
    }
    homepage_path = os.path.join(_repo_root_dir, '..', repo, 'homepage.html')
    _save_html('index', template_params, homepage_path)


def save_reports_type_indexes(report_types, global_config, league_names):
    for report_type in report_types:
        github = global_config[report_type]['github']
        all_leagues = defaultdict(list)
        reports_repo_name = global_config[report_type]['repo_name']
        reports_dir_name = global_config[report_type]['dir_name']
        reports_dir = os.path.join(_repo_root_dir, '..', reports_repo_name, reports_dir_name)
        for sports in _sports_keys:
            sports_reports_dir = os.path.join(reports_dir, sports)
            if not os.path.isdir(sports_reports_dir):
                continue
            for path in os.listdir(sports_reports_dir):
                if os.path.isdir(os.path.join(sports_reports_dir, path)):
                    all_leagues[sports].append(path)
        
        indexes = {}
        index_url_prefix = f'https://{github}.github.io/{reports_repo_name}/{reports_dir_name}'
        for sports in _sports_keys:
            for league_id in all_leagues[sports]:
                league_name = f'{league_names[sports][league_id]} ({_sports_to_display[sports]})'
                league_link = f'{index_url_prefix}/{sports}/{league_id}/index.html'
                indexes[league_name] = league_link
        
        template_params = {
            'title': f'Fantasy Fun Stuff ({report_type})',
            'indexes': indexes,
            'google_analytics_key': global_config[report_type]['google_analytics_key']
        }
        type_index_path = os.path.join(reports_dir, 'index.html')
        _save_html('type_index', template_params, type_index_path)


def save_league_index(league_name, league_settings, global_config):
    sports = league_settings['sports']
    league_id = league_settings['leagues'].split(',')[0]
    enable_analytics_flags = list(map(int, league_settings.get('is_analytics_enabled', '0').split(',')))
    index_keys = ['results', 'analytics'] if np.sum(enable_analytics_flags) != 0 else ['results']
    if league_settings['is_full_support']:
        index_keys.append('active stats')

    main_github = global_config['main_github']
    main_repo = global_config['main_repo']
    main_index_url = f'https://{main_github}.github.io/{main_repo}/homepage.html'
    for index_key in index_keys:
        index_repo_name = global_config[index_key]['repo_name']
        index_dir_name = global_config[index_key]['dir_name']
        index_relative_path = os.path.join(index_repo_name, index_dir_name, sports, league_id)
        home_page_dir = os.path.join(_repo_root_dir, '..', index_relative_path)
        Path(home_page_dir).mkdir(parents=True, exist_ok=True)

        indexes_by_year = []
        github = global_config[index_key]['github']
        dirs = [item for item in os.listdir(home_page_dir) if os.path.isdir(os.path.join(home_page_dir, item))]
        for season_str in sorted(dirs, reverse=True):
            season_relative_path = os.path.join(index_relative_path, season_str)
            season_reports, _ = _get_season_reports(season_relative_path, github)
            indexes_by_year.append([season_str, season_reports])

        template_params = {
            'title': f'Fantasy Fun Stuff ({index_key})',
            'index': main_index_url,
            'league_name': league_name,
            'league_link': f'https://fantasy.espn.com/{sports}/league?leagueId={league_id}',
            'sports': sports,
            'indexes_by_year': indexes_by_year,
            'google_analytics_key': global_config[index_key]['google_analytics_key']
        }
        league_home_path = os.path.join(home_page_dir, 'index.html')
        _save_html('league_home', template_params, league_home_path)


def save_tables(sports, tables, total_tables, league_id, league_name, matchup, schedule, global_config, report_type):
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'

    main_github = global_config['main_github']
    main_repo = global_config['main_repo']
    main_index_url = f'https://{main_github}.github.io/{main_repo}/homepage.html'

    github = global_config[report_type]['github']
    index_repo_name = global_config[report_type]['repo_name']
    index_dir_name = global_config[report_type]['dir_name']
    index_relative_path = os.path.join(index_repo_name, index_dir_name, sports, league_id, season_str)
    previous_reports_data = _get_previous_reports_data(index_relative_path, matchup, schedule, github)
    title = f'{league_name} ({sports}). Matchup {matchup} {report_type}'
    template_params = {
        'header': f'Fantasy Fun Stuff ({report_type})',
        'title': title,
        'index': main_index_url,
        'matchup': matchup,
        'leagues': tables,
        'total_tables': total_tables,
        'previous_reports': previous_reports_data,
        'google_analytics_key': global_config[report_type]['google_analytics_key']
    }
    report_dir = os.path.join(_repo_root_dir, '..', index_relative_path)
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    matchup_path = os.path.join(report_dir, f'matchup_{matchup}.html')
    _save_html ('matchup_report', template_params, matchup_path)

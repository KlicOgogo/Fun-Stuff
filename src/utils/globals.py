from collections import defaultdict
import json
import os


_repo_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
_config = {}
_league_names_path = os.path.join(_repo_root_dir, 'res/league_names.json')
_league_names = defaultdict(dict)
_titles = {}
_descriptions = {}
_category_names = {}
_data_loaded_matchups_path = os.path.join(_repo_root_dir, 'res/data_loaded_matchups.config')
_data_loaded_matchups = defaultdict(dict)

REPORT_TYPES = ('matchup_stats', 'analytics', 'active_stats')


def init_globals():
    category_names()
    config()
    descriptions()
    league_names()
    titles()
    data_loaded_matchups()


def category_names():
    global _category_names
    if _category_names:
        return _category_names
    category_names_path = os.path.join(_repo_root_dir, 'res/category_names.json')
    with open(category_names_path, 'r', encoding='utf-8') as category_names_fp:
        _category_names = json.load(category_names_fp)
    return _category_names


def config():
    global _config
    if _config:
        return _config

    config_path = os.path.join(_repo_root_dir, 'res/config.json')
    with open(config_path, 'r', encoding='utf-8') as config_fp:
        _config = json.load(config_fp)
    return _config


def descriptions():
    global _descriptions
    if _descriptions:
        return _descriptions
    
    descriptions_path = os.path.join(_repo_root_dir, 'res/descriptions.json')
    with open(descriptions_path, 'r', encoding='utf-8') as fp:
        _descriptions = json.load(fp)
    return _descriptions


def league_names():
    global _league_names
    if _league_names:
        return _league_names
    
    if os.path.isfile(_league_names_path):
        with open(_league_names_path, 'r', encoding='utf-8') as fp:
            names_json = json.load(fp)
            for sports in names_json:
                _league_names[sports].update(names_json[sports])
    return _league_names


def save_league_names():
    if _league_names:
        with open(_league_names_path, 'w', encoding='utf-8') as fp:
            json.dump(_league_names, fp, indent=4)


def titles():
    global _titles
    if _titles:
        return _titles
    
    titles_path = os.path.join(_repo_root_dir, 'res/titles.json')
    with open(titles_path, 'r', encoding='utf-8') as fp:
        _titles = json.load(fp)
    return _titles


def data_loaded_matchups():
    global _data_loaded_matchups
    if _data_loaded_matchups:
        return _data_loaded_matchups
    
    if os.path.isfile(_data_loaded_matchups_path):
        with open(_data_loaded_matchups_path, 'r', encoding='utf-8') as fp:
            flags_json = json.load(fp)
            for sports in flags_json:
                _data_loaded_matchups[sports].update(flags_json[sports])
    return _data_loaded_matchups


def save_data_loaded_matchups():
    if _data_loaded_matchups:
        with open(_data_loaded_matchups_path, 'w', encoding='utf-8') as fp:
            json.dump(_data_loaded_matchups, fp, indent=4)

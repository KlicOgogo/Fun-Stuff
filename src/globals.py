import os

from utils.json_utils import load as json_load

_repo_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
_config = {}
_titles = {}
_descriptions = {}
_category_names = {}


def category_names():
    global _category_names
    if not _category_names:
        category_names_path = os.path.join(_repo_root_dir, 'res/category_names.json')
        _category_names = json_load(category_names_path)
    return _category_names


def config():
    global _config
    if not _config: 
        config_path = os.path.join(_repo_root_dir, 'res/config.json')
        _config = json_load(config_path)
    return _config


def descriptions():
    global _descriptions
    if not _descriptions:
        descriptions_path = os.path.join(_repo_root_dir, 'res/descriptions.json')
        _descriptions = json_load(descriptions_path)
    return _descriptions


def titles():
    global _titles
    if not _titles:
        titles_path = os.path.join(_repo_root_dir, 'res/titles.json')
        _titles = json_load(titles_path)
    return _titles

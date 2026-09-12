import os
import traceback

from utils.common import save_homepage
from utils.json_utils import load as json_load
from utils.common import load_global_resources


def main():
    global_res = load_global_resources()
    global_config = global_res['config']

    res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'res')
    categories = json_load(os.path.join(res_dir, 'categories.json'))
    points = json_load(os.path.join(res_dir, 'points.json'))
    league_names = json_load(os.path.join(res_dir, 'league_names.json'))

    index_config = (categories or []) + (points or [])
    save_homepage(global_config, index_config, league_names or {})

    print('Homepage refreshed successfully.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()

import json
import os


def load(path, file_not_found_return=None):
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as fp:
            return json.load(fp)
    return file_not_found_return


def dump(obj, path):
    if obj:
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(obj, fp, indent=4)

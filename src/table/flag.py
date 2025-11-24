import numpy as np


_place_range = 0.3333333333
_score_range = 0.2


def _norm(place, place_list):
    return (place - 1) / (len(place_list) - 1)


def bottom_place(place, place_list):
    return _norm(place, place_list) > 1.0 - _place_range


def bottom_score(score, score_list):
    return np.mean(score_list) * (1.0 - _score_range) >= score


def half_bottom_score(score, score_list):
    mean_val = np.mean(score_list)
    return np.logical_and(mean_val * (1.0 - _score_range / 2) >= score, score > mean_val * (1.0 - _score_range))


def half_top_score(score, score_list):
    mean_val = np.mean(score_list)
    return np.logical_and(mean_val * (1.0 + _score_range / 2) <= score, score < mean_val * (1.0 + _score_range))


def top_place(place, place_list):
    return _norm(place, place_list) <= _place_range


def top_score(score, score_list):
    return np.mean(score_list) * (1.0 + _score_range) <= score

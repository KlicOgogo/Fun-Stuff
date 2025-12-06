import numpy as np

from table import flag


ATTRS = 'align= "center"'
ATTRS_SORTABLE = 'align="center"; class="sortable"'


def calculate_table_attributes(isSortable, hasPositionColumn):
    attributes = 'align="center"; '
    if isSortable:
        attributes += 'class="sortable"; '

    sticky_column_count = 2 if hasPositionColumn else 1
    attributes += f'data-sticky="{sticky_column_count}"; '
    return attributes


def _by_ranges(s, ranges, colors):
    result = []
    for v in s:
        for i, (range_left, range_right) in enumerate(ranges):
            if range_left < v <= range_right:
                result.append(f'background-color: {colors[i]}')
                break
    return result


def _score(s, is_opponent):
    flag_lambdas = [flag.top_score, flag.half_top_score, flag.half_bottom_score, flag.bottom_score]
    color_indexes = np.array([len(flag_lambdas) for _ in range(len(s))])
    for i in range(len(flag_lambdas)):
        color_indexes[flag_lambdas[i](s, s)] = i

    colors = ['blue', 'green', 'orange', 'red']
    if is_opponent:
        colors = list(reversed(colors))
    colors = colors + ['']
    return [f'color: {colors[i]}' for i in color_indexes]


def category_power(s):
    colors = ['darkgreen', 'green', '', 'red', 'darkred']
    n_ranks = len(colors)
    ranges = [(i * len(s) / n_ranks, (i + 1) * len(s) / n_ranks) for i in range(n_ranks)]
    return _by_ranges(s, ranges, colors)


def each_category_win_stat(s):
    colors = ['darkred', 'red', '', 'green', 'darkgreen']
    n_ranks = len(colors)
    ranges = [(-0.00001, 1 / n_ranks)] + [(i / n_ranks, (i + 1) / n_ranks) for i in range(1, n_ranks)]
    return _by_ranges(s, ranges, colors)


def extremum(s, best_value, worst_value):
    attr = 'background-color'
    return [f'{attr}: lightgreen' if v == best_value else f'{attr}: orange' if v == worst_value else '' for v in s]


def opponent_luck_score(v):
    return value(-v)


def opponent_place(s):
    return ['color: red' if flag.top_place(v, s) else 'color: blue' if flag.bottom_place(v, s) else '' for v in s]


def opponent_score(s):
    return _score(s, True)


def pair_result(v):
    color = 'darkred' if v == 'L' else 'black' if v == 'D' else 'darkgreen'
    return f'color: {color}'


def percentage(v):
    interval_width = 0.3333333333
    color = 'red' if v < interval_width else 'green' if v >= 1 - interval_width else 'black'
    return f'color: {color}'


def place(s):
    return ['color: blue' if flag.top_place(v, s) else 'color: red' if flag.bottom_place(v, s) else '' for v in s]


def score(s):
    return _score(s, False)


def value(v):
    color = 'red' if v < 0 else 'black' if v == 0 else 'green'
    return f'color: {color}'

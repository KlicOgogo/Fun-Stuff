
import copy

import numpy as np
import pandas as pd

from table import style
from table.common import add_position_column


_epsilon = 0.00000000001


def _calculate_player_rows(player, stats, all_categories, category_short):
    data_row = [player, ' ']
    columns_row = [' ']

    for cat in all_categories:
        if cat not in stats:
            continue

        if cat == 'FPTS':
            data_row.append('  ')
            columns_row.append('  ')
        data_row.append(stats[cat])
        columns_row.append(category_short[cat])

        if cat == 'Field Goals Attempted' and 'Field Goals Made' in stats and 'Field Goal Percentage' in category_short:
            fg_percentage = np.round(stats['Field Goals Made'] / (stats[cat] + _epsilon) * 100.0, 1)
            data_row.append(fg_percentage)
            columns_row.append(category_short['Field Goal Percentage'])
        if cat == 'Free Throws Attempted' and 'Free Throws Made' in stats and 'Free Throw Percentage' in category_short:
            ft_percentage = np.round(stats['Free Throws Made'] / (stats[cat] + _epsilon) * 100.0, 1)
            data_row.append(ft_percentage)
            columns_row.append(category_short['Free Throw Percentage'])
        if cat == 'Saves' and 'Goals Against' in stats and 'Save Percentage' in category_short:
            save_percentage = np.round(stats[cat] / (stats['Goals Against'] + stats[cat] + _epsilon) * 100.0, 1)
            data_row.append(save_percentage)
            columns_row.append(category_short['Save Percentage'])
        if cat == 'Minutes Played' and 'Goals Against' in stats and 'Goals Against Average' in category_short:
            gaa = np.round(stats['Goals Against'] * 60.0 / (stats[cat] + _epsilon), 2)
            data_row.append(gaa)
            columns_row.append(category_short['Goals Against Average'])
        if cat == 'FPTS' and 'Skater Games Played' in stats:
            fpg = np.round(stats[cat] / (stats['Skater Games Played'] + _epsilon), 1)
            data_row.append(fpg)
            columns_row.append('FPG')
        if cat == 'FPTS' and 'Games Started' in stats:
            fpg = np.round(stats[cat] / (stats['Games Started'] + _epsilon), 1)
            data_row.append(fpg)
            columns_row.append('FPG')

    return data_row, columns_row


def matchup(players_stats, categories_data):
    render_data = []
    category_columns = []
    all_categories, category_short = copy.deepcopy(categories_data)
    all_categories.append('FPTS')
    category_short['FPTS'] = 'FPTS'

    for player, stats in players_stats.items():
        stats_row, columns_row = _calculate_player_rows(player, stats, all_categories, category_short)
        if not category_columns:
            category_columns = columns_row
        render_data.append(stats_row)

    df = pd.DataFrame(render_data, index=np.arange(len(render_data)), columns=['Player'] + category_columns)
    all_sort_cols = ['PTS', 'GS', 'GP', 'MIN', 'FPTS']
    sort_cols = [col for col in all_sort_cols if col in category_columns]
    sort_indexes = np.lexsort([df[col] * -1.0 for col in sort_cols])
    df = df.iloc[sort_indexes]
    df = add_position_column(df)
    table_attrs = style.calculate_table_attributes(isSortable=True, hasPositionColumn=True)
    styler = df.style.format('{:g}', subset=list(set(category_columns) - {'ATOI', ' ', '  '})).\
        set_table_styles(style.STYLES).set_table_attributes(table_attrs).hide()
    return styler.to_html()

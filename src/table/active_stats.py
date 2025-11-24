
import copy

import numpy as np
import pandas as pd

from table import style
import utils.table

EPSILON = 0.00000000001


def matchup(players_stats, categories_data):
    render_data = []
    category_columns = []
    all_categories, categories_to_short = copy.deepcopy(categories_data)
    all_categories.append('FPTS')
    categories_to_short['FPTS'] = 'FPTS'
    
    for player, stats in players_stats.items():
        data_row = []
        columns_row = []
        data_row.append(player)
        data_row.append(' ')
        columns_row.append(' ')

        for cat in all_categories:
            if cat not in stats:
                continue

            if cat == 'FPTS':
                data_row.append('  ')
                columns_row.append('  ')
            data_row.append(stats[cat])
            columns_row.append(categories_to_short[cat])
            
            if cat == 'Field Goals Attempted' and 'Field Goals Made' in stats and 'Field Goal Percentage' in categories_to_short:
                fg_percentage = np.round(stats['Field Goals Made'] / (stats[cat] + EPSILON) * 100.0, 1)
                data_row.append(fg_percentage)
                columns_row.append(categories_to_short['Field Goal Percentage'])
            elif cat == 'Free Throws Attempted' and 'Free Throws Made' in stats and 'Free Throw Percentage' in categories_to_short:
                ft_percentage = np.round(stats['Free Throws Made'] / (stats[cat] + EPSILON) * 100.0, 1)
                data_row.append(ft_percentage)
                columns_row.append(categories_to_short['Free Throw Percentage'])
            elif cat == 'Saves' and 'Goals Against' in stats and 'Save Percentage' in categories_to_short:
                save_percentage = np.round(stats[cat] / (stats['Goals Against'] + stats[cat] + EPSILON) * 100.0, 1)
                data_row.append(save_percentage)
                columns_row.append(categories_to_short['Save Percentage'])
            elif cat == 'Minutes Played' and 'Goals Against' in stats and 'Goals Against Average' in categories_to_short:
                gaa = np.round(stats['Goals Against'] * 60.0 / (stats[cat] + EPSILON), 2)
                data_row.append(gaa)
                columns_row.append(categories_to_short['Goals Against Average'])
            elif cat == 'FPTS' and 'Skater Games Played' in stats:
                fpg = np.round(stats[cat] / (stats['Skater Games Played'] + EPSILON), 1)
                data_row.append(fpg)
                columns_row.append('FPG')
            elif cat == 'FPTS' and 'Games Started' in stats:
                fpg = np.round(stats[cat] / (stats['Games Started'] + EPSILON), 1)
                data_row.append(fpg)
                columns_row.append('FPG')

        if not category_columns:
            category_columns = columns_row
        render_data.append(data_row)

    df = pd.DataFrame(render_data, index=np.arange(len(render_data)), columns=['Player'] + category_columns)
    all_sort_cols = ['PTS', 'GS', 'GP', 'MIN', 'FPTS']
    sort_cols = [col for col in all_sort_cols if col in category_columns]
    sort_indexes = np.lexsort([df[col] * -1.0 for col in sort_cols])
    df = df.iloc[sort_indexes]
    df = utils.table.add_position_column(df)
    styler = df.style.format('{:g}', subset=list(set(category_columns) - {'ATOI', ' ', '  '})).\
        set_table_styles(style.STYLES).set_table_attributes(style.ATTRS_SORTABLE).hide()
    return styler.to_html()

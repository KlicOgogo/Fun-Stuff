from collections import defaultdict
import datetime
import os
import pickle
import re
import sys
import time

from bs4 import BeautifulSoup
import numpy as np
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options


class BrowserManager(object):
    def __init__(self, page_limit, sleep_timeout):
        self.__options = Options()
        self.__options.add_argument('--ignore-certificate-errors')
        self.__options.page_load_strategy = 'eager'

        self.__browser = Chrome(options=self.__options)
        self.__pageLimit = page_limit
        self.__sleep_timeout = sleep_timeout
        self.__pageCount = 0
        self.__loadTimeout = 30
        self.__browser.set_page_load_timeout(self.__loadTimeout)

    def read_page_source(self, url):
        if self.__pageCount == self.__pageLimit:
            self.clear()
            self.__browser = Chrome(self.__options)
            self.__pageCount = 0
            self.__browser.set_page_load_timeout(self.__loadTimeout)

        try:
            self.__browser.get(url)
        except TimeoutException as e:
            print(f'[Timeout] Page load exceeded limit for {url}: {e}', file=sys.stderr)
            time.sleep(self.__sleep_timeout)
            # Stop further resource loading so browser doesn't hang
            self.__browser.execute_script('window.stop();')
        except WebDriverException as e:
            print(f'[WebDriver error] Could not load {url}: {e}', file=sys.stderr)
            time.sleep(self.__sleep_timeout)
            # Optionally stop loading here too
            self.__browser.execute_script('window.stop();')
        finally:
            time.sleep(self.__sleep_timeout)

        self.__pageCount += 1
        html_soup = BeautifulSoup(self.__browser.page_source, features='html.parser')
        return html_soup

    def clear(self):
        self.__browser.quit()

    def __del__(self):
        self.clear()


_offline_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')


def _parse_box_scores_titles(tables):
    result = []
    for table_html in tables:
        subtable_list = table_html.findAll('table')

        columns_ordered = []
        columns_to_short = {}

        if not subtable_list:
            result.append((columns_ordered, columns_to_short))
            continue

        columns_html = subtable_list[1].findAll('tr', {'class': ['Table__even']})[-1]
        for item in columns_html.findAll('div', {'class': ['table--cell']}):
            categories = item['title']
            short_columns = item.text
            if len(categories.split(' & ')) > 1:
                for cat, val in zip(categories.split(' & '), short_columns.split('/')):
                    columns_ordered.append(cat)
                    columns_to_short[cat] = val
            else:
                columns_ordered.append(categories)
                columns_to_short[categories] = short_columns

        result.append((columns_ordered, columns_to_short))
    return result


def _parse_box_scores_data(tables):
    result = []
    for table_html in tables:
        subtable_list = table_html.findAll('table')

        if not subtable_list:
            result.append({})
            continue

        players = []
        for item in subtable_list[0].findAll('tr', {'class': ['Table__odd']}):
            player_name_html = item.findAll('div', {'class': ['player__column']})
            if len(player_name_html) == 1:
                players.append(player_name_html[0]['title'])

        player_stats = []
        players_html = subtable_list[1].findAll('tr', {'class': ['Table__odd']})
        for index, player_item in enumerate(players_html):
            if index >= len(players):
                continue
            player_stats_html = player_item.findAll('div', {'class': ['table--cell']})
            stats = {}
            for item in player_stats_html:
                categories = item['title']
                values = item.text
                if len(categories.split(' & ')) > 1:
                    for cat, val in zip(categories.split(' & '), values.split('/')):
                        stats[cat] = val
                else:
                    stats[categories] = values
            player_stats.append(stats)

        if len(subtable_list) > 2:
            players_html = subtable_list[2].findAll('tr', {'class': ['Table__odd']})
            for index, player_item in enumerate(players_html):
                if index >= len(players):
                    continue
                player_stats_html = player_item.findAll('div', {'class': ['table--cell']})
                stats = player_stats[index]
                if len(player_stats_html) == 1:
                    stats['FPTS'] = player_stats_html[0].text
        result.append({player: stat for player, stat in zip(players, player_stats)})
    return result


def _parse_box_scores_totals(tables):
    result = {}
    for table_html in tables:
        subtable_list = table_html.findAll('table')
        if len(subtable_list) >= 2:
            subtable = subtable_list[1]
            cols = subtable.findAll('tr', {'class': 'Table__sub-header'})[0].findAll('th')
            totals_vals = subtable.findAll('tr')[-1].findAll('td')
            for tot, col in zip(totals_vals, cols):
                result[col.text] = tot.text
    return result


def _format_cat_score(score_str, n_categories):
    score_components = list(map(int, score_str.split('-')))
    if len(score_components) == 2:
        return f'{score_components[0]}-{score_components[1]}-{n_categories - np.sum(score_components)}'
    return score_str


def _get_matchup_date(matchup_text):
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    start_end_str = re.findall(r'\((.+)\)', matchup_text)[0]
    start_str, end_str = map(lambda x: x.strip().lstrip(), start_end_str.split('-'))
    start_components = start_str.split(' ')
    start_month = months[start_components[0].lower()]
    start_day = int(start_components[1])
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    start_year = season_start_year if start_month > 6 else season_start_year + 1
    end_components = end_str.split(' ')
    end_month = start_month if len(end_components) == 1 else months[end_components[0].lower()]
    end_day = int(end_components[0]) if len(end_components) == 1 else int(end_components[1])
    end_year = season_start_year if end_month > 6 else season_start_year + 1
    get_day = lambda year, month, day: datetime.datetime(year=year, month=month, day=day).date()
    return (get_day(start_year, start_month, start_day), get_day(end_year, end_month, end_day))


def _get_matchup_number(matchup_text):
    matches = re.findall(r'Matchup (\d+)', matchup_text)
    if len(matches) == 1:
        return int(matches[0]), False
    playoffs_matches = re.findall(r'Playoff Round (\d+)', matchup_text)
    if len(playoffs_matches) == 1:
        return int(playoffs_matches[0]), True
    return None, None


def _get_matchup_schedule(matchup_text, prev_matchup_number):
    matchup_number, is_playoffs = _get_matchup_number(matchup_text)
    if matchup_number is None:
        return []
    if is_playoffs:
        matchup_number = prev_matchup_number + 1
    matchup_date = _get_matchup_date(matchup_text)
    return matchup_number, matchup_date, is_playoffs


def _get_matchup_scores(scoreboard_html, team_names, league_id, league_name):
    matchup_scores = []
    for scoreboard_row in scoreboard_html.findAll('div', {'class': 'Scoreboard__Row'}):
        res = []
        for team_data_html in scoreboard_row.findAll('li', 'ScoreboardScoreCell__Item'):
            team_id_a_tag = team_data_html.findAll('a', {'class': 'AnchorLink'})
            team_id = re.findall(r'teamId=(\d+)', team_id_a_tag[0]['href'])[0]
            team = (team_names[team_id], team_id, league_name, league_id)
            score_str = team_data_html.findAll('div', {'class': 'ScoreCell__Score'})[0].text

            if len(score_str.split('-')) == 1:
                score = float(score_str)
            else:
                rows = scoreboard_row.findAll('tr', {'class': 'Table__TR'})
                categories = [header.text for header in rows[-3].findAll('th', {'class': 'Table__TH'})[1:]]
                score = _format_cat_score(score_str, len(categories))
            res.append((team, score))
        matchup_scores.append(res)
    return matchup_scores


def _get_team_names(scoreboard_html):
    team_names = {}
    for scoreboard_row in scoreboard_html.findAll('div', {'class': 'Scoreboard__Row'}):
        for team_data_html in scoreboard_row.findAll('li', 'ScoreboardScoreCell__Item'):
            team_id_a_tag = team_data_html.findAll('a', {'class': 'AnchorLink'})
            team_id = re.findall(r'teamId=(\d+)', team_id_a_tag[0]['href'])[0]
            team_name = team_data_html.findAll('div', {'class': 'ScoreCell__TeamName'})[0].text
            team_names[team_id] = team_name
    return team_names


def _box_scores_offline(league_id, league_name, team_names, sports, matchup):
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'
    offline_box_scores_dir = os.path.join(_offline_data_dir, sports, league_id, season_str)

    offline_data_path = os.path.join(offline_box_scores_dir, f'box_scores_{matchup}.pkl')
    if os.path.isfile(offline_data_path):
        with open(offline_data_path, 'rb') as fp:
            box_scores_stats = pickle.load(fp)
            box_scores_stats_updated = {}
            for old_team_key, stats in box_scores_stats.items():
                team_id = old_team_key[1]
                actual_team_key = (team_names[team_id], team_id, league_name, league_id)
                box_scores_stats_updated[actual_team_key] = stats
            return box_scores_stats_updated
    return None


def _box_scores_online(league_id, sports, matchup, pairs, group_schedule, browser):
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1

    scoring_period_id = (group_schedule[matchup][0][0] - group_schedule[1][0][0]).days + 1
    box_scores_stats = {}
    for pair in pairs:
        team_pair = (pair[0][0], pair[1][0])
        url = (f'https://fantasy.espn.com/{sports}/boxscore?leagueId={league_id}&matchupPeriodId={matchup}'
               f'&scoringPeriodId={scoring_period_id}'
               f'&seasonId={season_start_year + 1}&teamId={team_pair[0][1]}&view=matchup')

        data_html = []
        while len(data_html) == 0:
            html_soup = browser.read_page_source(url)
            data_html = html_soup.findAll(
                ['div', 'span'], {'class': ['players-table__sortable', 'team-name truncate']})

        tables_pairs = [[], []]
        current_team_index = -1
        for table_or_name in data_html:
            if table_or_name.name == 'span':
                current_team_index += 1
            else:
                tables_pairs[current_team_index].append(table_or_name)

        for player, tables in zip(team_pair, tables_pairs):
            box_scores_titles = _parse_box_scores_titles(tables)
            box_scores_data = _parse_box_scores_data(tables)
            box_scores_totals = _parse_box_scores_totals(tables)
            box_scores_stats[player] = (box_scores_titles, box_scores_data, box_scores_totals)

    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'
    offline_box_scores_dir = os.path.join(_offline_data_dir, sports, league_id, season_str)
    os.makedirs(offline_box_scores_dir, exist_ok=True)
    offline_data_path = os.path.join(offline_box_scores_dir, f'box_scores_{matchup}.pkl')
    with open(offline_data_path, 'wb') as fp:
        pickle.dump(box_scores_stats, fp)
    return box_scores_stats


def group_box_scores(group_settings, group_schedule, matchup, browser, scoreboards, online_page_matchups):
    if not group_settings['is_full_support']:
        return None

    sports = group_settings['sports']
    box_scores = defaultdict(list)
    for league in group_settings['leagues']:
        pairs, team_names, _, league_name = scoreboards[league]
        for m in range(matchup):
            current_matchup = m + 1
            is_offline = current_matchup not in online_page_matchups
            matchup_box_scores = None
            if is_offline:
                matchup_box_scores = _box_scores_offline(
                    league, league_name, team_names, sports, current_matchup)
            if matchup_box_scores is None:
                matchup_box_scores = _box_scores_online(
                    league, sports, current_matchup, pairs[m], group_schedule, browser)
            box_scores[league].append(matchup_box_scores)

    return box_scores


def goalkeeper_games(matchup_box_scores):
    if not matchup_box_scores:
        return None
    gk_games = {}
    for team, (_, _, box_scores_totals) in matchup_box_scores.items():
        gk_games[team] = int(box_scores_totals['GS']) if 'GS' in box_scores_totals else 0
    return gk_games if np.sum(list(gk_games.values())) != 0 else None


def _matchup_category_pairs(scoreboard_html, league_id, league_name, team_names):
    pairs = []
    for scoreboard_row in scoreboard_html.findAll('div', {'class': 'Scoreboard__Row'}):
        opponents = scoreboard_row.findAll('li', 'ScoreboardScoreCell__Item')
        team_ids = []
        for o in opponents:
            team_id_a_tag = o.findAll('a', {'class': 'AnchorLink'})
            team_id = re.findall(r'teamId=(\d+)', team_id_a_tag[0]['href'])[0]
            team_ids.append(team_id)
        teams = [(team_names[team_id], team_id, league_name, league_id) for team_id in team_ids]
        rows = scoreboard_row.findAll('tr', {'class': 'Table__TR'})
        categories = [header.text for header in rows[-3].findAll('th', {'class': 'Table__TH'})[1:]]
        first_team_stats = [data.text for data in rows[-2].findAll('td', {'class': 'Table__TD'})[1:]]
        second_team_stats = [data.text for data in rows[-1].findAll('td', {'class': 'Table__TD'})[1:]]

        pair = []
        for team, team_stats in zip(teams, [first_team_stats, second_team_stats]):
            stats = []
            for cat, stat in zip(categories, team_stats):
                if cat == 'ATOI':
                    minutes = stat.split(':')[0]
                    formatted_stat = f'0{stat}' if int(minutes) < 10 else stat
                    stats.append((cat, formatted_stat))
                else:
                    stats.append((cat, float(stat)))
            pair.append((team, stats))
        pairs.append(tuple(pair))
    return pairs, categories


def minutes(matchup_box_scores_data):
    if not matchup_box_scores_data:
        return None
    minutes = {}
    for team, (_, _, box_scores_totals) in matchup_box_scores_data.items():
        minutes[team] = int(box_scores_totals['MIN']) if 'MIN' in box_scores_totals else 0
    return minutes if np.sum(list(minutes.values())) != 0 else None


def player_games(matchup_box_scores_data):
    if not matchup_box_scores_data:
        return None
    player_games = {}
    for team, (_, _, box_scores_totals) in matchup_box_scores_data.items():
        player_games[team] = int(box_scores_totals['GP']) if 'GP' in box_scores_totals else 0
        player_games[team] += int(box_scores_totals['GS']) if 'GS' in box_scores_totals else 0
    return player_games if np.sum(list(player_games.values())) != 0 else None


def _schedule(league_id, sports, is_playoffs_support, is_offline, browser):
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'
    offline_data_dir = os.path.join(_offline_data_dir, sports, league_id, season_str)
    os.makedirs(offline_data_dir, exist_ok=True)

    offline_schedule_path = os.path.join(offline_data_dir, 'schedule.pkl')
    if os.path.isfile(offline_schedule_path) and is_offline:
        with open(offline_schedule_path, 'rb') as fp:
            league_schedule = pickle.load(fp)
            return league_schedule

    schedule_url = f'https://fantasy.espn.com/{sports}/league/schedule?leagueId={league_id}'

    div_captions = None
    caption_captions = None
    while not div_captions and not caption_captions:
        schedule_html = browser.read_page_source(schedule_url)
        div_captions = schedule_html.findAll('div', {'class': 'table-caption'})
        caption_captions = schedule_html.findAll('caption', {'class': 'Table__Caption'})

    league_schedule = {}
    number = 0
    for matchups_html_list in [div_captions, caption_captions]:
        for matchup_html in matchups_html_list:
            number, dates, is_playoffs = _get_matchup_schedule(matchup_html.text, number)
            if not is_playoffs or is_playoffs_support:
                league_schedule[number] = (dates, is_playoffs)

    with open(offline_schedule_path, 'wb') as fp:
        pickle.dump(league_schedule, fp)
    return league_schedule


def group_schedule(group_settings, browser, use_offline_schedule):
    schedule = None
    sports = group_settings['sports']
    for league in group_settings['leagues']:
        current_schedule = _schedule(
            league, sports, group_settings['is_playoffs_support'], use_offline_schedule, browser)
        if schedule is None:
            schedule = current_schedule
        elif schedule != current_schedule:
            schedule = None
            break

    return schedule


def scoreboards(league_id, sports, matchup, browser, online_matchups, is_category_league):
    today = datetime.datetime.today().date()
    season_start_year = today.year if today.month > 6 else today.year - 1
    season_str = f'{season_start_year}-{str(season_start_year + 1)[-2:]}'
    offline_scoreboard_dir = os.path.join(_offline_data_dir, sports, league_id, season_str)
    os.makedirs(offline_scoreboard_dir, exist_ok=True)

    soups = []
    espn_scoreboard_url = f'https://fantasy.espn.com/{sports}/league/scoreboard'
    for m in range(1, matchup + 1):
        html_soup = None
        while html_soup is None or html_soup.find('div', {'class': 'Scoreboard__Row'}) is None:
            matchup_html_path = os.path.join(offline_scoreboard_dir, f'matchup_{m}.html')
            if m in online_matchups or not os.path.exists(matchup_html_path):
                scoreboard_url = f'{espn_scoreboard_url}?leagueId={league_id}&matchupPeriodId={m}'
                html_soup = browser.read_page_source(scoreboard_url)
                with open(matchup_html_path, 'w', encoding='utf-8') as html_fp:
                    html_fp.write(str(html_soup))
            else:
                html_soup = BeautifulSoup(open(matchup_html_path, 'r', encoding='utf-8'), features='html.parser')
        soups.append(html_soup)

    league_name = soups[-1].findAll('h3')[0].text
    team_names = _get_team_names(soups[-1])

    scores = []
    category_pairs = []
    for m in range(matchup):
        scores.append(_get_matchup_scores(soups[m], team_names, league_id, league_name))
        if is_category_league:
            matchup_category_pairs = _matchup_category_pairs(soups[m], league_id, league_name, team_names)
            category_pairs.append(matchup_category_pairs)
    return scores, team_names, category_pairs, league_name

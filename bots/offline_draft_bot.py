from collections import defaultdict
import datetime
import json
import os
import sys
import time

import pytz
from telegram.ext import MessageHandler, Filters, Updater


CONFIG = {}
DATA = {}
DATA_PATH = ''
MINSK_TZ = pytz.timezone('Europe/Minsk')
TIMEOUT = 30
request_kwargs = {
    'read_timeout': TIMEOUT,
    'connect_timeout': TIMEOUT,
}
UPDATER = None


def read_config():
    global CONFIG
    league_name = sys.argv[1]
    with open(f'{league_name}.json', 'r', encoding='utf-8') as fp:
        CONFIG = json.load(fp)
    return league_name


def is_draft_active():
    all_picks = sum(DATA['draft_picks'].values(), [])
    return DATA['pick_number'] <= max(all_picks)


def generate_default_data():
    if not CONFIG:
        return {}
    default_data = {
        'pick_number': 1,
    }
    
    n_hours_start = CONFIG['start_day_hour']
    draft_start_day = datetime.datetime.strptime(CONFIG['start_date'], '%Y-%m-%d').date()
    draft_start_day = datetime.datetime.combine(draft_start_day, datetime.datetime.min.time())
    draft_start_time = draft_start_day + datetime.timedelta(seconds=3600 * n_hours_start)
    default_data['last_pick_time'] = draft_start_time.strftime('%Y-%m-%d %H:%M:%S')
    
    default_data['reserve_time'] = {team: CONFIG['reserve_time'] for team in CONFIG['draft_order']}

    default_data['draft_picks'] = defaultdict(list)
    current_pick = default_data['pick_number']
    for round_number in range(1, CONFIG['rounds'] + 1):
        draft_order = CONFIG['draft_order']
        order = reversed(draft_order) if round_number % 2 == 0 and CONFIG['is_snake_draft'] else draft_order
        for team in order:
            default_data['draft_picks'][team].append(current_pick)
            current_pick += 1

    return default_data


def load_data():
    if not os.path.isfile(DATA_PATH):
        return generate_default_data()
    with open(DATA_PATH, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def error_message(context, update, caption):
    context.bot.send_photo(
        chat_id=update.effective_chat.id, 
        photo='https://s00.yaplakal.com/pics/pics_original/3/9/6/15712693.jpg',
        reply_to_message_id=update.message.message_id, 
        caption=caption)


def echo(update, context):
    if 'tag' not in CONFIG:
        raise Exception('Config is not read')
    tag = CONFIG['tag']
    if not update.message or not update.message.text or update.message.text[:len(tag)] != tag:
        return
    rows = list(map(lambda x: x.strip(), update.message.text.strip().split('\n')))
    rows = [r for r in rows if r]
    if len(rows) != 2 or rows[0] != tag:
        error_message(context, update, 'Ошибка в теге или в формате сообщения (должно быть 2 строчки: тег и пик)')
        return

    if '.' not in rows[1]:
        error_message(context, update, "Ошибка: за номером пика должна стоять точка.\nНапример: 1. Royce O'Neale")
        return

    divisor_index = rows[1].index('.')

    ### player name ###
    player_name = rows[1][divisor_index+1:].lstrip().rstrip()
    player_name_comp = player_name.split(' ')
    if len(player_name_comp) < 2 or len(player_name_comp) > 3:
        error_message(context, update, 'Ошибка в имени и фамилии игрока')
        return
    if len(player_name_comp) == 3 and player_name_comp[2] not in ['III', 'Jr.', 'Sr.', 'IV']:
        error_message(context, update, 'Ошибка в имени и фамилии игрока')
        return
    ### player name ###
    
    global DATA
    DATA = load_data()

    if 'chat' not in DATA:
        DATA['chat'] = update.effective_chat.id
    elif DATA['chat'] != update.effective_chat.id:
        error_message(context, update, 'Драфт проводится не в этом чате')
        return


    ### pick number ###
    if str(DATA['pick_number']) != rows[1][:divisor_index]:
        error_message(context, update, 'Ошибка в номере пика')
        return

    DATA['pick_number'] += 1
    
    ### pick number ###    
    
    ### messages dates ###
    n_hours_start = CONFIG['start_day_hour']
    n_hours_end = CONFIG['end_day_hour']

    prev_pick_time = datetime.datetime.strptime(DATA['last_pick_time'], '%Y-%m-%d %H:%M:%S').astimezone(MINSK_TZ) 
    today_time = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    
    current_pick_time = update.message.date.astimezone(MINSK_TZ)
    if current_pick_time < prev_pick_time:
        current_pick_time = prev_pick_time
    elif current_pick_time.hour >= n_hours_end:
        current_pick_time = today_time + datetime.timedelta(seconds=3600 * n_hours_end)
    elif current_pick_time.hour < n_hours_start:
        current_pick_time = today_time - datetime.timedelta(seconds=3600 * (24 - n_hours_end))
    elif prev_pick_time.day < current_pick_time.day:
        prev_pick_time = (today_time + datetime.timedelta(seconds=3600 * n_hours_start)).astimezone(MINSK_TZ)
    current_pick_time = current_pick_time.astimezone(MINSK_TZ)

    DATA['last_pick_time'] = current_pick_time.strftime('%Y-%m-%d %H:%M:%S')
    ### messages dates ###
    
    ### other data ###
    usernames = CONFIG['usernames']
    picks = DATA['draft_picks']
    
    next_pick = DATA['pick_number']
    team_by_pick = {p: team for team, team_picks in picks.items() for p in team_picks}
    team_to_pick = team_by_pick[next_pick - 1]
    time_to_pick = current_pick_time - prev_pick_time
    
    reserve_time_lost = max(0, time_to_pick.seconds - CONFIG['base_time'])
    reserve_time = DATA['reserve_time']
    reserve_time[team_to_pick] = max(0, reserve_time[team_to_pick] - reserve_time_lost)
    ### other data ###
    
    ### create respond message ###
    reserve_timedelta = datetime.timedelta(seconds=reserve_time[team_to_pick])
    msg = f'Команда {team_to_pick} выбирает под номером {next_pick-1} игрока {player_name}!\n' \
        + f'Время на пик: {(datetime.datetime.min + time_to_pick).time().strftime("%H:%M:%S")}, ' \
        + f'оставшееся время в резерве: {(datetime.datetime.min + reserve_timedelta).time().strftime("%H:%M:%S")}.\n'
    if next_pick - 1 < len(team_by_pick):
        next_team = team_by_pick[next_pick]
        msg += f'Следующими выбирает команда {next_team} ({usernames[next_team]}) под номером {next_pick}\n\n'
    if next_pick < len(team_by_pick):
        msg += 'В очереди:\n'
        cur_team = team_by_pick[next_pick + 1]
        msg += f'1. {cur_team} ({usernames[cur_team]})\n'
    if next_pick + 1 < len(team_by_pick):
        cur_team = team_by_pick[next_pick + 2]
        msg += f'2. {cur_team} ({usernames[cur_team]})\n'
    fmt = '%Y-%m-%d %H:%M:%S'
    if next_pick - 1 < len(team_by_pick):
        time_pick = current_pick_time + datetime.timedelta(seconds=CONFIG['base_time'])
        if time_pick.hour >= n_hours_end or time_pick.hour < n_hours_start:
            time_pick += datetime.timedelta(seconds=3600 * (24 - n_hours_end + n_hours_start))
        msg += f'Ожидаемое время выбора команды {next_team}: {time_pick.strftime(fmt)},' 
        reserve_time_pick = time_pick + datetime.timedelta(seconds=reserve_time[next_team])
        if reserve_time_pick.hour >= n_hours_end or reserve_time_pick.hour < n_hours_start:
            reserve_time_pick += datetime.timedelta(seconds=3600 * (24 - n_hours_end + n_hours_start))
        msg += f' с учётом резерва: {reserve_time_pick.strftime(fmt)}\n\n'
    else:
        msg += "Драфт завершён, всем спасибо!\n\n"
    msg += CONFIG['admin_tag']
    
    context.bot.sendMessage(
        chat_id=update.effective_chat.id, 
        text=msg,
        reply_to_message_id=update.message.message_id,
        timeout=TIMEOUT)
    ### create respond message ###

    with open(DATA_PATH, 'w', encoding='utf-8') as fp:
        json.dump(DATA, fp, indent=4)


def main():
    league_name = read_config()
    UPDATER = Updater(token=CONFIG['bot_token'], request_kwargs=request_kwargs)
    global DATA_PATH
    DATA_PATH = f'{league_name}_data.json'
    global DATA
    DATA = load_data()
    while is_draft_active():
        echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
        UPDATER.dispatcher.add_handler(echo_handler)
        UPDATER.start_polling()
        
        dt = datetime.datetime.now() + datetime.timedelta(seconds=300)
        while datetime.datetime.now() < dt:
            if not is_draft_active():
                break

            time.sleep(1)
        
        UPDATER.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if UPDATER.running:
            UPDATER.stop()
        main()

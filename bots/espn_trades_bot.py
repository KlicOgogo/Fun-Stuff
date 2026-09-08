from collections import defaultdict
import datetime
import time

import pytz
from telegram.ext import MessageHandler, Filters, Updater


minsk_tz = pytz.timezone('Europe/Minsk')
n_hours_start = 10
n_hours_end = 22
timeout = 5
TOKEN = '' # insert bot token here
request_kwargs = {
    'read_timeout': timeout,
    'connect_timeout': timeout,
}
UPDATER = Updater(token=TOKEN, request_kwargs=request_kwargs)


def echo(update, context):
    if not update.message or not update.message.text or update.message.text[:6] != '#trade':
        return
    rows = list(map(lambda x: x.strip(), update.message.text.strip().split('\n')))
    trade_assets = defaultdict(str)
    for row in rows:
        row_data = list(map(lambda x: x.lstrip().strip(), row.split('traded')))
        if len(row_data) != 2:
            continue
        team = row_data[0]
        asset = row_data[1].split(' to ')[0].lstrip().strip()
        trade_assets[team] += ' + ' + asset

    trade_items = list(trade_assets.items())
    if len(trade_items) != 2:
        return
    first_team = trade_items[0][0]
    first_team_assets = trade_items[1][1][3:]
    second_team = trade_items[1][0]
    second_team_assets = trade_items[0][1][3:]
    message = context.bot.sendPoll(
        chat_id=update.effective_chat.id, 
        question = f'Трейд!\n{first_team} получает {first_team_assets}\n{second_team} получает {second_team_assets}\n',
        options = [
            'Одобряю трейд',
            f'Вето: {first_team} получает слишком много',
            f'Вето: {second_team} получает слишком много',
            'Участник трейда или коммиш'
        ],
        is_anonymous=False, allow_sending_without_reply=True,
        timeout=timeout
    )
    today_time = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()).astimezone(minsk_tz)
    notification_deadline_left = today_time + datetime.timedelta(seconds=3600 * n_hours_start)
    notification_deadline_right = today_time + datetime.timedelta(seconds=3600 * n_hours_end)
    
    current_time = datetime.datetime.now().astimezone(minsk_tz)
    is_disable_notification = current_time < notification_deadline_left or current_time > notification_deadline_right

    context.bot.pinChatMessage(
        chat_id=update.effective_chat.id,
        message_id=message.message_id, 
        disable_notification=is_disable_notification
    )


def main():
    while True:
        echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
        UPDATER.dispatcher.add_handler(echo_handler)
        UPDATER.start_polling()
        
        dt = datetime.datetime.now() + datetime.timedelta(seconds=300)
        while datetime.datetime.now() < dt:
            time.sleep(1)
        
        UPDATER.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if UPDATER.running:
            UPDATER.stop()
        main()
        print("Restarted by Exception")

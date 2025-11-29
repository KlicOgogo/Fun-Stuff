import datetime
import json
import os
import time
import traceback

import git
from telegram import Bot

import index
import utils.globals


_repo_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
_bot = None


def _send_bot_message(text, is_debug, is_delayed):
    bot_settings_path = os.path.join(_repo_root_dir, 'res', 'bot.config')
    with open(bot_settings_path, 'r', encoding='utf-8') as fp:
        bot_settings = json.load(fp)
    
    if is_delayed:
        time.sleep(bot_settings['sleep_time'])
    
    global _bot
    if not _bot:
        _bot = Bot(token=bot_settings['token'])
    channel = bot_settings['debug_channel'] if is_debug else bot_settings['channel']
    parse_mode = None if is_debug else 'Markdown'
    _bot.send_message(chat_id=channel, text=text, parse_mode=parse_mode, timeout=30)


def main():
    _send_bot_message('\U0001f608 Chef is cooking', True, False)
    config = utils.globals.config()

    for report_type in utils.globals.REPORT_TYPES:
        repo = config[report_type]['repo_name']
        branch = config[report_type]['branch']
        ssh_key = config[report_type]['ssh_key']

        repo_path = os.path.join(_repo_root_dir, '..', repo)
        git_repo = git.Repo.init(repo_path)
        git_repo.git.reset('--hard')
        git_repo.git.clean('-df')
        git_repo.git.checkout(branch)
        git_repo.git.pull('origin', branch, env={"GIT_SSH_COMMAND": f'ssh -i ~/.ssh/{ssh_key}'})

    index.main()

    for report_type in utils.globals.REPORT_TYPES:
        repo = config[report_type]['repo_name']
        branch = config[report_type]['branch']
        ssh_key = config[report_type]['ssh_key']

        repo_path = os.path.join(_repo_root_dir, '..', repo)
        git_repo = git.Repo.init(repo_path)
        git_repo.git.add('.')
        today = datetime.datetime.today().date()
        if git_repo.is_dirty():
            git_repo.git.commit('-m', f'Run and commit executed {today.strftime("%Y-%m-%d")}')
            git_repo.git.push('origin', branch, env={"GIT_SSH_COMMAND": f'ssh -i ~/.ssh/{ssh_key}'})

    message_text = (
        '\U0001fae1 Таблицы по матчапам, которые закончились на прошлой неделе, посчитаны.\n'
        '\U0001f440 Смотреть: https://klicogogo.github.io/Fantasy-Fun-Stuff/homepage.html.\n'
        '\U0001f970 Благодарность, обратная связь, вопросы, дикпики: в комментариях.\n'
        '\U0001f92d На книги по успешному успеху, который меня ждёт после ухода из фентези: '
        '[YooMoney](https://yoomoney.ru/to/4100116057812582).'
    )
    _send_bot_message(message_text, False, True)


if __name__ == '__main__':
    start_time = time.time()
    try:
        main()
    except Exception as e:
        exception_str = traceback.format_exc()
        _send_bot_message(exception_str, True, False)
        print(exception_str)
    finally:
        finish_time = time.time()
        _send_bot_message(f'Время выполнения: {finish_time - start_time:.2f} секунд', True, False)

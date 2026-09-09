# Bots Documentation

---

## ESPN Trades Bot

Бот читает сообщения в чате и создаёт опросы по трейдам с закрепом, если у него есть права. Работает одновременно во всех чатах, куда добавлен.

### Формат сообщения

1. `#trade` — первая строка, которая позволяет боту понять, что это сообщение ему необходимо обработать.
2. Дальше вставляется сообщение из **Recent activity** фентези-лиги ESPN о трейде. Например:

```
Bees traded Pavel Zacha, Bos C to Medical Assistance
Bees traded Kevin Fiala, LA LW to Medical Assistance
Medical Assistance traded Timo Meier, NJ LW to Bees
Medical Assistance traded Wyatt Johnston, Dal C to Bees
```

### Пример полного сообщения для бота

```
#trade
Bees traded Pavel Zacha, Bos C to Medical Assistance
Bees traded Kevin Fiala, LA LW to Medical Assistance
Medical Assistance traded Timo Meier, NJ LW to Bees
Medical Assistance traded Wyatt Johnston, Dal C to Bees
```

### Примечания

1. Запущенный бот может проигнорировать первое сообщение о трейде. Как правило, на второе и последующие он должен отреагировать.

2. У бота есть ограничение на размер сообщения опроса, который он может создать. Так получается, если в трейде было задействовано слишком много активов. В этом случае рекомендуется объединять несколько активов трейда в один.

**Пример слишком длинного сообщения:**

```
#trade 
Medical Assistance traded 21st Round Draft Pick (336th Overall) to Dahlin ex-Jesus
Medical Assistance traded 22nd Round Draft Pick (337th Overall) to Dahlin ex-Jesus
Medical Assistance traded 14th Round Draft Pick (209th Overall) to Dahlin ex-Jesus
Medical Assistance traded 13th Round Draft Pick (208th Overall) to Dahlin ex-Jesus
Dahlin ex-Jesus traded 18th Round Draft Pick (274th Overall) to Medical Assistance
Dahlin ex-Jesus traded 17th Round Draft Pick (271st Overall) to Medical Assistance
Dahlin ex-Jesus traded 16th Round Draft Pick (242nd Overall) to Medical Assistance
Dahlin ex-Jesus traded 15th Round Draft Pick (239th Overall) to Medical Assistance
```

**Можно преобразовать в:**

```
#trade
Medical Assistance traded 21st, 22nd Round Draft Pick (336th, 337th Overall) to Dahlin ex-Jesus
Medical Assistance traded 13th, 14th Round Draft Pick (208th, 209th Overall) to Dahlin ex-Jesus
Dahlin ex-Jesus traded 17th, 18th Round Draft Pick (271st, 274th Overall) to Medical Assistance
Dahlin ex-Jesus traded 15th, 16th Round Draft Pick (239th, 242nd Overall) to Medical Assistance
```

Без потери смысла.

3. В теории бот может работать постоянно, но как будто проще его запускать его каждый раз на один трейд, если их немного, а компьютер, на котором запускается бот, может выключаться.

### Запуск бота

Чтобы запустить бота, нужно выполнить следующие шаги:

0. Скачать код. Например, `git clone https://github.com/KlicOgogo/Fun-Stuff.git` или скачать архив.
1. Установить Python (подойдёт 3.9): https://www.python.org/downloads/release/python-390/. Для Windows качается и устанавливается как любая другая программа.
2. Установить нужные библиотеки Python. Для этого нужно открыть командную строку в папке с ботом и выполнить команду:
   ```bash
   pip install -r requirements.txt
   ```
   > Чтобы открыть командную строку в папке с ботом, нужно зайти в неё в проводнике, кликнуть на путь, напечатать `cmd` и нажать `ENTER`.
3. Создать бота в [@BotFather](https://t.me/BotFather). Там нужно выдать боту доступ к сообщениям чата, а также извлечь **API Token**, который нужен для его запуска.
   
   > ⚠️ **Важно:** API Token нельзя шарить никому, чтобы он не мог попасть в руки мошенников, которые от имени вашего бота смогут любой код запустить, в том числе незаконный.
4. Подставить токен в файл `espn_trades_bot.py` в 13 строке. Например, если токен — `VLASTELIN_KUBOV`, то должно получиться:
   ```python
   TOKEN = 'VLASTELIN_KUBOV'
   ```
5. Запустить из командной строки бота, выполнив команду:
   ```bash
   python espn_trades_bot.py
   ```

---

## Offline Draft Bot

Для запуска бота для драфта необходимо подготовить файл конфига `{league_name}.json` следующего формата:

```json
{
    "bot_token": "token from botfather",
    "rounds": 10,
    "is_snake_draft": true,
    "base_time": 10800,
    "reserve_time": 9000,
    "tag": "#draft2023",
    "start_date": "2024-04-30",
    "admin_tag": "@klicunou",
    "start_day_hour": 10,
    "end_day_hour": 22,
    "usernames": {
        "Балтика Черри-Блейзерс": "@top, @norm",
        "BC Total eclipse": "@poolepoker, Jokic",
        "ODESSA MAMA": "JPorter, @brefDroch",
        "Bulls on Fire": "@lameloEnjoyer, @Alex",
        "Sir Elton Drog": "@pivoDreamer, @Dumayuwi",
        "Bald Reborn": "@johhny, @sins",
        "Truth Wolves": "@lesnoy, volchara",
        "Свидетели Аналитики": "@galygin, ."
    },
    "draft_order": [
        "BC Total eclipse",
        "Балтика Черри-Блейзерс",
        "ODESSA MAMA",
        "Bulls on Fire",
        "Sir Elton Drog",
        "Bald Reborn",
        "Truth Wolves",
        "Свидетели Аналитики"
    ]
}
```

### Формат файла

Словарь, где настройки имеют формат: `"setting_name": "setting_value"`.

### Список необходимых настроек

| Настройка | Описание | Тип |
|-----------|----------|-----|
| `bot_token` | Уникальный идентификатор Telegram бота | строка |
| `rounds` | Число раундов офлайн-драфта | число |
| `is_snake_draft` | Флаг типа драфта | логический (`true` — драфт-змейка, `false` — традиционный формат, как в NBA) |
| `base_time` | Базовое время (даётся на каждый выбор) | число (секунды) |
| `reserve_time` | Резервное время (даётся на весь драфт и используется, когда команда не уложилась в базовое время) | число (секунды) |
| `tag` | Хэштег драфта | строка. Используется как часть формата сообщения для распознавания ботом |
| `start_date` | День старта драфта | строка вида `YYYY-MM-DD` |
| `admin_tag` | Тег для уведомления распорядителя драфта (обычно комиссионер лиги) | строка |
| `start_day_hour` | Час начала активного времени драфта (с этого времени время на пик начинает идти) | число |
| `end_day_hour` | Час завершения активного времени драфта (с этого времени время на пик перестаёт идти) | число |
| `usernames` | Юзернеймы участников офлайн-драфта, используются для оповещения игроков | объект: `{"team1": "team1_usernames", ...}` |
| `draft_order` | Список команд по порядку офлайн-драфта | массив: `["team1", "team2", ...]` |

### Формат сообщения для бота

```
#draft2024
1. Royce O'Neale
```

**Расшифровка:**
- `#draft2024` — конкретное значение настройки `tag`
- `1` — номер пика
- `.` — разделитель
- `Royce O'Neale` — имя и фамилия (обязательно ровно из двух слов) игрока. Возможно использование `Jr.`, `Sr.`, `III`, `IV`.

### Запуск бота

Аналогично боту espn_trades_bot, только токен нужно вставить в json-файл с настройками для лиги.

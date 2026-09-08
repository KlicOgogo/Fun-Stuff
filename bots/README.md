Бот читает сообщения в чате и создаёт опросы по трейдам с закрепом, если у него есть права. Работает одновременно во всех чатах, куда добавлен. Формат сообщения следующий:
1. #trade - первая строка, которая позволяет боту понять, что это сообщение ему необходимо обработать.
2. Дальше вставляется сообщение из Recent activity фентези-лиги ESPN о трейде. Например:
Bees traded Pavel Zacha, Bos C to Medical Assistance
Bees traded Kevin Fiala, LA LW to Medical Assistance
Medical Assistance traded Timo Meier, NJ LW to Bees
Medical Assistance traded Wyatt Johnston, Dal C to Bees 

Пример полного сообщения для бота выглядит следующим образом:
#trade
Bees traded Pavel Zacha, Bos C to Medical Assistance
Bees traded Kevin Fiala, LA LW to Medical Assistance
Medical Assistance traded Timo Meier, NJ LW to Bees
Medical Assistance traded Wyatt Johnston, Dal C to Bees

Примечания:
1. Запущенный бот может проигнорировать первое сообщение о трейде. Как правило, на второе и последующие он должен отреагировать.

2. У бота есть ограничение на размер сообщения опроса, которй он может создать. Так получается, если в трейде было задействовано слишком много активов. В этом случае рекомендуется объединять несколько активов трейда в один. 

Например, слишком длинное сообщение:
#trade 
Medical Assistance traded 21st Round Draft Pick (336th Overall) to Dahlin ex-Jesus
Medical Assistance traded 22nd Round Draft Pick (337th Overall) to Dahlin ex-Jesus
Medical Assistance traded 14th Round Draft Pick (209th Overall) to Dahlin ex-Jesus
Medical Assistance traded 13th Round Draft Pick (208th Overall) to Dahlin ex-Jesus
Dahlin ex-Jesus traded 18th Round Draft Pick (274th Overall) to Medical Assistance
Dahlin ex-Jesus traded 17th Round Draft Pick (271st Overall) to Medical Assistance
Dahlin ex-Jesus traded 16th Round Draft Pick (242nd Overall) to Medical Assistance
Dahlin ex-Jesus traded 15th Round Draft Pick (239th Overall) to Medical Assistance

Можно преобразовать в: 
#trade
Medical Assistance traded 21st, 22nd Round Draft Pick (336th, 337th Overall) to Dahlin ex-Jesus
Medical Assistance traded 13th, 14th Round Draft Pick (208th, 209th Overall) to Dahlin ex-Jesus
Dahlin ex-Jesus traded 17th, 18th Round Draft Pick (271st, 274th Overall) to Medical Assistance
Dahlin ex-Jesus traded 15th, 16th Round Draft Pick (239th, 242nd Overall) to Medical Assistance

Без потери смысла.

3. В теории бот может работать постоянно, но как будто проще его запускать его каждый раз на один трейд, если их немного, а компьютер, на котором запускается бот, может выключаться.

Чтобы запустить бота, нужно выполнить следующие шаги:
0. Скачать и распаковать архив с кодом.
1. Установить питон, подойдёт 3.9: https://www.python.org/downloads/release/python-390/. Для Windows качается и устанавливается как любая другая программа.
2. Установить нужные библиотеки питона. Для этого нужно открыть командную строку в папке с ботом и выполнить команду:
pip install -r requirements.txt
Чтобы открыть командную строку в папке с ботом, нужно зайти в неё в проводнике, кликнуть на путь, напечатать cmd и нажать ENTER.
3. Бот, созданный в @BotFather. Там нужно выдать боту доступ к сообщениям чата, а также извлечь API Token, который нужен для его запуска. 
API Token нельзя шарить никому, чтобы он не мог попасть в руки мошенников, которые от имени вашего бота смогут любой код запустить, в том числе незаконный.
4. Подставить токен в файл espn_trades_bot.py в 13 строке. Например, если токен - VLASTELIN_KUBOV, то должно получиться:
TOKEN = 'VLASTELIN_KUBOV'
5. Запустить из командной строки бота, выполнив команду:
python espn_trades_bot.py

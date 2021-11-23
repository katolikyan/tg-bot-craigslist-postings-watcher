import os
import telebot
import logging
import time
import json
import threading
from dotenv import load_dotenv
from Listener import Listener


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('tg_bot.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


# HELPERS

def load_json():
    with open('./users.json', 'r') as f:
        return json.load(f)


def dump_json(data):
    with open('./users.json', 'w') as f:
        json.dump(data, f, indent=4)


class fake_chat():

    def __init__(self, uid):
        self.id = uid

class fake_message():

    def __init__(self, uid):
       self.chat = fake_chat(uid)


# END HELPERS


# SETUP

load_dotenv()
API_KEY = os.getenv('API_KEY')

g_bot = telebot.TeleBot(API_KEY)
telebot.logger.setLevel(logging.INFO) # Outputs debug messages to console.

g_users = load_json()

g_apps = {}

# END SETUP



def initialized(chat_id):
    if chat_id not in g_apps:
        g_bot.send_message(chat_id,
                        'Your app was not found. Try /init first\n'
                        'Possible Reasons:\n'
                        '  1. You have never used the bot\n'
                        '  2. Bot\'s prod server got down\n'
                        )
        return None
    return 1



@g_bot.message_handler(commands=['init'])
def __init__(message):
    if message.chat.id in g_apps.keys():
        g_bot.send_message(message.chat.id, f'App has already been inited')
        return

    global g_users
    user_data = None
    if str(message.chat.id) in g_users.keys():
        user_data = g_users[str(message.chat.id)]
        g_bot.send_message(message.chat.id, f'App restored')
    else:
        g_users[message.chat.id] = {}
        dump_json(g_users)
        g_bot.send_message(message.chat.id, f'New App created')

    g_apps[message.chat.id] = Listener(user_data)



@g_bot.message_handler(commands=['run'])
def __run__(message):
    if not initialized(message.chat.id): return
    if g_apps[message.chat.id].is_running():
        g_bot.send_message(message.chat.id, f'The app is already watching.. ')
        return

    container = []
    g_apps[message.chat.id].start(container)
    g_bot.send_message(message.chat.id, f'Started watching postings')


    def _loop():
        while g_apps[message.chat.id].is_running():
            if len(container) > 0:
                for item in container:
                    g_bot.send_message(message.chat.id,
                                    f"Title: {item['title']}\n"
                                    f"Price: {item['price']}\n"
                                    f"Link: {item['link']}\n"
                                    f"Date: {item['date']}\n"
                    )
                    time.sleep(0.5)
                container.clear()
            time.sleep(25)

    tread = threading.Thread(target=_loop)
    tread.start()



@g_bot.message_handler(commands=['stop'])
def __stop__(message):
    if not initialized(message.chat.id): return
    g_apps[message.chat.id].stop()
    g_bot.send_message(message.chat.id, f'Stopped watching postings')



@g_bot.message_handler(commands=['list'])
def __list__(message):
    if not initialized(message.chat.id): return
    list_of_links = g_apps[message.chat.id].list()
    bot_resp = 'Currently watching links: \n'
    for name, link in list_of_links.items():
        bot_resp += f"{name}: {link}\n"
    g_bot.send_message(message.chat.id, bot_resp)



def add_query_is_valid(message):
    req = message.text.split()
    if len(req) > 3:
        g_bot.send_message(message.chat.id, f'Too many arguments for "add" command, should be "/add name link" ')
        logger.debug(f"{message.from_user.username} {message.chat.id}: Too many args for add: {req}")
        return False
    if len(req) < 3:
        g_bot.send_message(message.chat.id, f'Not enough arguments for "add" command, should be "/add name link" ')
        logger.debug(f"{message.from_user.username} {message.chat.id}: Too few args for add: {req}")
        return False
    if not req[2].startswith('https://') and not req[2].startswith('http://'):
        g_bot.send_message(message.chat.id, f'Seems like 2nd argument is not a link')
        logger.debug(f"{message.from_user.username} {message.chat.id}: Not a link in add: {req}")
        return False
    return True

@g_bot.message_handler(commands=['add'])
def __add__(message):
    if not initialized(message.chat.id): return
    if not add_query_is_valid(message): return
    query = message.text.split()
    if g_apps[message.chat.id].add(query[1], query[2]):
        data = load_json()
        data[message.chat.id] = g_apps[message.chat.id].list()
        dump_json(data)

    g_bot.reply_to(message, f'Added {query[1]} to watchig list')



def remove_query_is_valid(message):
    req = message.text.split()
    if len(req) > 2:
        g_bot.send_message(message.chat.id, f'Too many arguments for "remove" command, should be "/remove name" ')
        logger.debug(f"{message.from_user.username} {message.chat.id}: To many args for /remove: {req}")
        return False
    if len(req) < 2:
        g_bot.send_message(message.chat.id, f'Not enough arguments for "remove" command, should be "/remove name" ')
        logger.debug(f"{message.from_user.username} {message.chat.id}: To few args for /remove: {req}")
        return False
    return True

@g_bot.message_handler(commands=['remove'])
def __remove__(message):
    if not initialized(message.chat.id): return
    if not remove_query_is_valid(message): return
    name = message.text.split('/remove ')[1]
    removed = g_apps[message.chat.id].remove(name)
    if not removed:
        g_bot.send_message(message.chat.id, f'Couldn\'t remove {name} from the list. Please double check the spelling')
        logger.debug(f"{message.from_user.username} {message.chat.id}: Couldn't remove in the Listener")
    else:
        data = load_json()
        data[str(message.chat.id)].pop(name)
        dump_json(data)
        g_bot.send_message(message.chat.id, f'Successfully removed {name} from the list')



@g_bot.message_handler(commands=['help'])
def __help__(message):
    g_bot.send_message(message.chat.id,
    f'''
    Posting listener bot v.0.1.0

    /help - shows this help :)
    /init - use it first time you run the bot. Or if bot database is down :(
    /list - prints list of links you are watching
    /add <NAME> <LINK> - add a link with a nameID to the list of links to watch
    /remove <NAME> - remove a link from watching by providing the nameID
    /run - start watching for updates
    /stop - stop watching for updates

    links can be dinamically added during watching. no need to stop
    ''')


@g_bot.message_handler(func=lambda x: True)
def default(message):
    g_bot.reply_to(message, f'Couldn\'t recognize command')



# PRERUN

for user_id, settings in g_users.items():
    g_apps[int(user_id)] = Listener(settings)
    g_bot.send_message(int(user_id), f'Bad news: Server was restarted :(\nGood news: Your settings were restored :)')
    __run__(fake_message(int(user_id)))

print(f"{len(g_apps)} Apps restored")
logger.info(f"{len(g_apps)} Apps restored")


# RUN

g_bot.infinity_polling(logger_level=logging.DEBUG, timeout=10, long_polling_timeout = 5)
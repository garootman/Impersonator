import openai
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import re
import sqlite3
from bot_config import *
import os
import json
from datetime import datetime, timedelta

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials

global me, currmoney, channels_data, noted_of_money_shortage


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_API_KEY_FILE



def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# Initialize Telegram Bot
bot = Bot(token=TG_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Connect to SQLite database
conn = sqlite3.connect(DB_FILE)
conn.row_factory = dict_factory
cursor = conn.cursor()

# Init OpenAI
openai.api_key = openai_key
# init google translate


def calc_USD_spent (tokens_spent, model=DEFAULT_TEXT_MODEL):
    if model[:3] =='img':
        return AI_MODELS[model]['ktoken_price']
    else:
        if model not in AI_MODELS:
            model = DEFAULT_MODEL
        return tokens_spent / 1000 * AI_MODELS[model]['ktoken_price']
    
    
def non_english_symbols_regex(string: str):
    pattern = re.compile(r'[^\x20-\x7E]')
    return pattern.findall(string)



async def get_openai_response (prompt, model=DEFAULT_TEXT_MODEL):
    max_tokens = max(200, min(MAX_REQUEST_LENGHT - CONTIGENCY - estimate_token_count(prompt), 4095))
    try:
        resp = await openai.Completion.acreate(
            engine=model,
            prompt=prompt,
            max_tokens=max_tokens,
            n=1,
            stop="###",
            temperature=TEMPERATURE,
        )
        token_used = int(resp["usage"]["total_tokens"] )
        resp = str(resp.choices[0].text).strip()
        success = True
    except Exception as e:
        success = False
        resp = (f"OpenAI error:\n{str(e)}")
        token_used = 0
    return resp, token_used, success


def estimate_token_count(prompt):
    estimated_token_count = 0
    words = prompt.split()
    for word in words:
        if len(non_english_symbols_regex(word)) > 1:
            estimated_token_count+=TOKENS_PER_WORD['rus']
        else:
            estimated_token_count+=TOKENS_PER_WORD['eng']
    estimated_token_count = int(estimated_token_count)
    estimated_token_count += len([i for i in prompt if re.sub(r'[\w\s]+', '', i, flags=re.UNICODE)])
    return int(estimated_token_count)


async def generate_vision (prompt, model=DEFAULT_IMAGE_MODEL):
    try:
        response = await openai.Image.acreate(prompt=prompt, n=1, size=model.replace('img',''))
        resp = response['data'][0]['url']
        success = True
    except Exception as e:
        resp = f"Error generating image:\n{str(e)}"
        success = False
    return resp, success

def trim_context(txt, model=DEFAULT_TEXT_MODEL):
    if model not in AI_MODELS: model = DEFAULT_TEXT_MODEL
    max_tokens = AI_MODELS[model]['maxtokens']
    remain_tokens =  max_tokens - CONTIGENCY - estimate_token_count(txt)
    context_tokens = int(remain_tokens * (1-ANSWER_RATIO))

    cont = []
    for line in txt.splitlines()[::-1]:
        str_to_lcont = str(cont + ['1'] + [line])
        str_to_lcont = str_to_lcont.replace("'",'')
        str_to_lcont = str_to_lcont.replace("[",'')
        str_to_lcont = str_to_lcont.replace("]",'')

        if estimate_token_count(str_to_lcont) < context_tokens:
            cont.append(line)
    ret_cont = ""
    for line in cont[::-1]:
        ret_cont = ret_cont + '\n' + line
    return ret_cont


def get_tovary():
    if TOVARY_FILE in os.listdir():
        with open(TOVARY_FILE, 'r', encoding='utf-8') as file:
            tovary = json.load(file)
        tovary = {int(i):tovary[i] for i in tovary}
    else:
        tovary = {}
    
    return tovary


def get_message(what, lang):
    init_what = what
    lang = lang.lower()
    what = what.lower()
    if MESSAGE_FILE not in os.listdir():
        print ("Message file not found, creating it")
        messages = {
            'default_message':{'eng':"There is no mesage text for this case. Add it to messages file", 'rus':"Нет текста сообщения по этому случаю. Добавьте сообщение в соответствующем файле."}
        }
        with open(MESSAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False)

    try:
        with open(MESSAGE_FILE, 'r', encoding='utf-8') as file:
            messages = json.load(file)
    except Exception as e:
        print (f"Messages file is corrupt, returning default_message. Error\n{str(e)}")
        what = 'default_message'

    if what not in messages:
        print (f"Message for {what} not found, returnin default.")
        what = 'default_message'

    if lang not in messages[what]:
        if list(messages[what].keys())[0]:
            print (f"Message for {what} in {lang} not found, returning {list(messages[what].keys())[0]}")
            lang = list(messages[what].keys())[0]
        else:
            print (f"Message for {what} has no languages, returning default_message")
            what = 'default_message'
            lang = 'eng'

    msg = messages[what][lang]
    if what == 'default_message':
        msg += '\n' + init_what
    return msg

def get_channels_to_sub():
    # Load subscribed channels from text file
    if CHANNELS_FILE not in os.listdir():
        with open(CHANNELS_FILE, 'w',encoding='utf-8') as f:
            f.write('\n')

    with open(CHANNELS_FILE, 'r',encoding='utf-8') as file:
        chanlines = file.read().splitlines()

    retlist = []
    for line in chanlines:
        try:
            x = int(line.strip())
        except:
            x = None
        if x:
            retlist.append(x)
            
    return retlist


class balance():
    def __init__(self):
        if OPENAI_BALANCE_FILE not in os.listdir():
            self.__value = ADMIN_API_NOTIFY_LIMIT_USD
            print (f"set default balance {self.value}")
        else:
            with open (OPENAI_BALANCE_FILE, 'r',encoding='utf-8') as f:
                self.__value = float(f.read())
            print (f"Got balance from file: {self.value}")
    @property
    def value(self):
        return self.__value
    
    @value.setter
    def value(self, val):
        self.__value = val
        print (f"Updated balance: {val}")
        with open (OPENAI_BALANCE_FILE, 'w',encoding='utf-8') as f:
            f.write(str(val))
            
            
def get_translate_service():
    credentials = GoogleCredentials.get_application_default()
#    credentials = GoogleCredentials.get_application_default().create_scoped ("https://www.googleapis.com/auth/cloud-platform")
    http = httplib2.Http()
    credentials.authorize(http)
    
    creds = GoogleCredentials.get_application_default()
    creds.authorize(http)
    # Create a service object
    translate_service = discovery.build('translate', 'v2')#, http=http)
    
    # Create a service object
#    service = discovery.build('translate', 'v3', http=http, discoveryServiceUrl=DISCOVERY_URL)
    return translate_service

def translate_to_lang(texts, target_lang):
    response = translate_service.translations().list(q=texts,target=target_lang).execute()
    return [i['translatedText'] for i in response['translations']][0]
         
def detect_lang(texts):
    response = translate_service.detections().list(q=texts).execute()
    return response['detections'][0][0]['language']


async def get_chan_data():
    channels_data = {i:{} for i in get_channels_to_sub()}
    nochans = []
    for chan in channels_data:
        try:
            channels_data[chan]['chat'] = await bot.get_chat(chan)
        except Exception as e:
            nochans.append(chan)
            print(f"could NOT find channel {chan}: {str(e)}")
            
    channels_data = {i:channels_data[i] for i in channels_data if i not in nochans}

    return channels_data

def utc(): return datetime.utcnow().replace(microsecond=0)
def dt(tt):  
    if type(tt)==str:
        return datetime.strptime(tt,"%Y-%m-%d %H:%M:%S")
    else: return tt
    
async def prospam(text, chatlist):
    succ = 0
    for chat_id in chatlist:
        try:
            chat = await bot.get_chat(chat_id)
            if chat.type != 'channel':
                await bot.send_message(int(chat_id), text)
                succ+=1
        except Exception as e:
            print (f"An error occurred while trying to send the message to user {chat_id}. Error: {e}")
    return succ

    

me = None
channels_data = None
currmoney = balance()
last_spent = 0
noted_of_money_shortage = False

translate_service = get_translate_service()

print("Bot and stuff initiated!")

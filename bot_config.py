# ACCESSES
openai_key="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"
#TG_TOKEN = "5954787913:AAHuAA9n0_CqJfRMPXGmOj7Kg-ntof11puE" # My OpenAI ChatGPT bot
TG_TOKEN = "5566311336:AAE4MBVzFjBL8DdliyhP7tE5Qs6o9PMynUA" # STRIPE TEST BOT
NOWPAYMENTS_KEY = "87Y9HHA-GEZ4TB9-HA1S789-JXBWMTS" # PROD
ADMIN_ID = 62408647               # тот у кого будет доступ к админ-командам
CONTACT_ADMIN_URL = "https://t.me/mr_garuda/" # ссылка для "написать админу". может быть любой
BINANCE_USER_MAIL = "dksg87@gmail.com"


# MODULES
USE_ROLE_MODELS = True
USE_SHOP = True
USE_VISION = True
USE_BALANCE_MONEY = True
USE_TRANSLATE_TO_ENG = True
USE_CONTACT_ADMIN = True
USE_CONTEXT_MGMT = True

#GROUP_LINK = "https://t.me/test0group01"
GROUP_LINK = ""

CHAT_ANSWER_FREQUENCY = 2 # как часто отвечать в групповых чатах, сколько сообщений пропускать.
CHANNEL_ANSWER_FREQUENCY = 2 # как часто писать ответы на посты в каналах

SUBSCRIBE_CHECK_TIMEOUT = 5 * 60  # как часто проверять подписку на каналы, в секундах. час = 60 * 60 = 3600


# FINANCE
ADMIN_API_NOTIFY_LIMIT_USD = 10
RATES_TO_USD = {'EUR': 0.921, 'RUB':73.1, 'USD':1.0}   # курсы валют. тут задаются, меняются админ-командами. 
INITIAL_DEMO_USD_BALANCE = 0.20    # сколько денег зачислять юзеру при старте общения 
REFERAL_INVITATION_BONUS = 0.20   # сколько денег начислять за реферала
TARIF_MODIFICATOR = 2.0


# PAYMENTS!
PAYMENT_METHODS = {
#    1:{'name':"Stripe TEST 🌍", 'currency':'EUR', 'token':"1284685063:TEST:ODAwMzIwM2NlMWU3"},
#    2:{'name':"TEST Bank 131 🤑", 'currency':'RUB','token':"1842663557:TEST:d3e7464425e583f03684835138f434418e57c312"},
#    3:{'name':"TEST PSB ❤️", 'currency':'RUB','token':"1832575495:TEST:9b2e724d1c672cdaa2ec0418f1732a9bb12991769134eadd23bf7145c9ea391f"},

    99:{'name':"Ю.Касса TEST valkli 🇷🇺", 'currency':'USD','token':"381764678:TEST:49221"},
}
#99 - это тестовый тип платежа, будет только у админа.

CRYPTO_PAYMENT_METHODS = {
    20:{'name':'USDT TRC20 TRX', 'currency':'usdttrc20'}, 
    21:{'name':'Ethereum ETH', 'currency':'eth'}, 
    22:{'name':'USDT Binance BSC', 'currency':'usdtbsc'}, 
    23:{'name':'Ripple XRP', 'currency':'xrp'}, 
                         }



# OpenAI parameters
ANSWER_RATIO = 0.4  # отношение максимальной длины ответа сетки к длине вопроса. 0.4 значит что 60% объёма на вопрос, 40% - на ответ
CONTEXT_LEN = 10    # какой длины хвост из сообщений тянуть в контекст. 10 - это 5 запросов и 5 ответов
MAX_REQUEST_LENGHT = 4095   # сколько токенов максимально на весь запрос-ответ. максимум - 4096. можно экспериментировать.
TOKENS_PER_WORD = {"rus":9.5, 'eng':2.2}
CONTIGENCY = 1000   # запас токенов на каждый запрос, на всякий случай
TEMPERATURE = 0.5 # температура запроса. читать мануалы чтобы понять что это


DEFAULT_TEXT_MODEL = 'gpt-3.5-turbo'
DEFAULT_IMAGE_MODEL = 'img512x512'


AI_MODELS = {
    'gpt-3.5-turbo':{'maxtokens':4095, 'ktoken_price_complete':0.002, },
    'gpt-4':{'maxtokens':8192, 'ktoken_price_complete':0.06, 'ktoken_price_context':0.03},
    'text-davinci-003':{'maxtokens':4000, 'ktoken_price_complete':0.02, },
    'text-curie-001':{'maxtokens':2048, 'ktoken_price_complete':0.002, },
    'text-babbage-001':{'maxtokens':2048, 'ktoken_price_complete':0.0005, },
    'text-ada-001':{'maxtokens':2048, 'ktoken_price_complete':0.0004, },
    'code-davinci-002':{'maxtokens':8000, 'ktoken_price_complete':0.02, },
    'code-cushman-001':{'maxtokens':2048, 'ktoken_price_complete':0.02, },
    
    'img1024x1024':{'maxtokens':0, 'image_price':0.02, },
    'img512x512':{'maxtokens':0, 'image_price':0.018, },
    'img256x256':{'maxtokens':0, 'image_price':0.016, },
            }


MESSAGE_FILE  = "messages.json"
CHANNELS_FILE = "channels.txt"
TOVARY_FILE = "tovary.json"
OPENAI_BALANCE_FILE = 'balance.txt'
GOOGLE_API_KEY_FILE = "./ai-with-radix-09328f41ef89.json"
ROLE_MODELS_FILE = 'role_models.json'
DB_FILE = "impersonator_bot_data.db"
CHAT_DUMP_FILE = 'all_chats.json'

ROLES_IN_ROW = 2

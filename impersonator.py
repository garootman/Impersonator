
import json
import asyncio
from datetime import datetime, timedelta
import os
import random


# In[2]:


from ai_tg_bot import *


# In[3]:


class Form (StatesGroup):
    broadcast_users = State() # Задаем состояние
    broadcast_chats = State() # Задаем состояние
    state_set_curr_api_balance = State()
    vision_mode = State()
    set_eur_rate = State()
    set_rub_rate = State()
    ban_somebody = State()
    un_ban_somebody = State()
    give_user_money = State()


# In[4]:


def get_role_models():
    with open (ROLE_MODELS_FILE,'r',encoding='utf-8') as f:
        role_models = json.load(f)
    role_models = {int(i):role_models[i] for i in role_models}
    return role_models


# In[5]:


# Create table for storing user data
cursor.execute('''CREATE TABLE IF NOT EXISTS user_data
                  (user_id INTEGER PRIMARY KEY, name TEXT, lang TEXT, balance REAL, banned INTEGER, subscribed INTEGER, ban_comment TEXT, subs_timestamp DATETIME)''')

# Create table for referals
cursor.execute('''CREATE TABLE IF NOT EXISTS referals
                  (host_id INTEGER, guest_id INTEGER, timestamp DATETIME)''')


# Create table for user chats
cursor.execute('''CREATE TABLE IF NOT EXISTS chat_data
                  (chat_id INTEGER PRIMARY KEY, owner_id INTEGER, title TEXT,role_id INTEGER, skipped INTEGER, type TEXT)''')

# Create table for balance data
cursor.execute('''CREATE TABLE IF NOT EXISTS money_acions
                  (user_id INTEGER, chat_id INTEGER, description TEXT, amount REAL, timestamp DATETIME)''')

# Create table for chat history
cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                  (chat_id INTEGER, user_id INTEGER, role_id INTEGER, message TEXT, tokens INTEGER, timestamp DATETIME)''')
conn.commit()    

#cursor.execute("PRAGMA table_info(chat_data)")
#columns = [col['name'] for col in cursor.fetchall()]

#if "last_sub_upd" not in columns:
#    cursor.execute("ALTER TABLE user_data ADD COLUMN last_sub_upd DATETIME")
#    cursor.execute("UPDATE user_data set last_sub_upd = ?", (datetime(2010,1,1),))
#    conn.commit() 

#cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#tables = cursor.fetchall()
#print(tables)
# In[6]:


async def send_msg (chat_id, text, photo = None, reply_markup=None, reply_to_message_id = None, note_admin = False):
    args = {'chat_id':chat_id,'reply_markup':reply_markup, 'reply_to_message_id':reply_to_message_id}
    
    if len(text.strip())==0 and not photo:
        print (f"No content to send. False.")
        return False
    
    if (photo):
        chunklen = 1024
        fnc = bot.send_photo
        txt_field = 'caption'
        args ['photo'] = photo
    else:
        chunklen = 4096
        fnc = bot.send_message
        txt_field = 'text'
    texts_to_send = ['']
    for l in text.splitlines():
        if len (texts_to_send[-1] +'\n'+ l) <=chunklen:
            texts_to_send[-1]+='\n'+l.strip()
        else:
            if len(l)<=chunklen:
                texts_to_send.append(l.strip())
            else:
                for w in l.split():
                    if len (texts_to_send[-1] +' '+ w) <=chunklen:
                        texts_to_send[-1]+=' '+w
                    else:
                        texts_to_send.append(w)
                        
    texts_to_send = [i.strip() for i in texts_to_send]
    
    
    try:
        for txt in texts_to_send:
            args[txt_field] = txt
            res = await fnc(**args)    
            await asyncio.sleep(1)

        return res
        
    except Exception as e:
        err_msg = (f"Could NOT send message to {chat_id}: {str(e)}")
        print (err_msg)
        if note_admin:
            await send_msg(ADMIN_ID, text=err_msg)
        return False


# In[7]:


async def send_invoice (chat_id, tovar_id, method_id):
    tovary = get_tovary()
    tovar = tovary[tovar_id]
    method = PAYMENT_METHODS[method_id]
    prices = [LabeledPrice(label=tovar['title'], amount=int(tovar['price'] * RATES_TO_USD[method['currency']]))]
    string = tovar['title']
    payload = f"tovar_{tovar_id}"
    invoice = await bot.send_invoice(chat_id = chat_id, 
                     title = tovar['title'], 
                     description = tovar['description'], 
                     payload = payload,
                     provider_token = method['token'],
                     currency = method['currency'],
                     prices = prices, 
#                     need_email=True,
#                     need_phone_number=True,
#                     start_parameter="test", 
                     photo_url= tovar['image_url'],
                     photo_size=tovar['img_size'],
                     photo_height = tovar['img_size'],
                     photo_width=tovar['img_size'],
                     is_flexible = False,
    )


# In[8]:


async def check_subscriptions(user_id):
    subbed = {0:True}

    try:
        user_chat = await bot.get_chat(user_id)
    except:
        return subbed, False
    
    for chan in channels_data:
        subbed[chan] = False
        try:
            subchan = await bot.get_chat_member(chat_id=chan, user_id=user_id)
            if subchan.status in ['administrator', 'member', 'creator']:
                subbed[chan] = True
        except:
            pass
    status = min([subbed[i] for i in subbed])
    return subbed, status


# In[9]:


async def send_unsub_message(user_id, user_data, send_true = False):
    subbed, status = await check_subscriptions(user_id)
    channels_data  = await get_chan_data()
    markup = InlineKeyboardMarkup()
    print (user_data)
    send = True
    if user_data['name'] =='Group (@GroupAnonymousBot)':
        status = True
        send = False
    if not status:
        msg = get_message('not_subbed', user_data['lang'])
        for chan in channels_data:
            if not subbed[chan]:
                chandict = channels_data[chan]['chat'].to_python()
                channel_button = InlineKeyboardButton(text=chandict.get('title'), url=chandict.get('invite_link'))
                markup.add(channel_button)
        check_button = InlineKeyboardButton(text="❓ Check", callback_data="check")
        markup.add(check_button)
        
        succ = await send_msg (user_id, msg, reply_markup=markup)  
            
    else:
        user_data['subscribed'] = True
        
    if (send_true) and status and send:
        msg = get_message('subbed', user_data['lang']).format(user_data['balance'])
        succ = await send_msg (user_id, msg, reply_markup=markup)  
        
    save_user_data(user_data, True)
    return status


# In[10]:


async def check_balance_warn():
    global noted_of_money_shortage
    global currmoney
    if currmoney.value <= ADMIN_API_NOTIFY_LIMIT_USD and not(noted_of_money_shortage):
        msg = get_message('little_money', 'eng').format(round(currmoney.value,4))
        succ = await send_msg (ADMIN_ID, msg)
        noted_of_money_shortage = True


# In[11]:


async def get_user_data(user_id):
    global channels_data, me
    print (user_id)
    if (not me) or (channels_data == None):
        channels_data  = await get_chan_data()
        me = await bot.get_me()
    # считать данные
    cursor.execute('SELECT * FROM user_data WHERE user_id=?', (user_id,))
    user_data = cursor.fetchone()
    cursor.execute("SELECT * FROM money_acions WHERE user_id=? and description LIKE '%payment%'", (user_id,))
    paid_users = cursor.fetchall()
    # если нет данных - завести в нужных таблицах, если есть - взять значения оттуда.
    if not user_data:
        try:
            chat = await bot.get_chat(user_id)
        except:
            return {}
        title = f"{chat.full_name} (@{chat.username})"
        user_data = {'user_id': user_id, 'name':title,'lang': 'eng', 'balance': INITIAL_DEMO_USD_BALANCE, 'banned': 0, 'subscribed': 0, 'ban_comment': '', 'subs_timestamp': utc()-timedelta(days=1000)}
        cursor.execute('INSERT INTO user_data (user_id, name, lang, balance, banned, subscribed, ban_comment, subs_timestamp) VALUES (?,?,?,?,?,?,?,?)'
            ,(user_id, title, 'eng', INITIAL_DEMO_USD_BALANCE, 0, 0, "", utc()))
        conn.commit()   
        add_money_action(user_id, user_id, INITIAL_DEMO_USD_BALANCE, 'demo balance')
    user_data['subs_timestamp'] = dt(user_data['subs_timestamp'])
    
    if (paid_users):
        # если платник - всё ок
        user_data['subscribed'] = True

    if not user_data['subscribed'] or (utc()-user_data['subs_timestamp']).total_seconds() > SUBSCRIBE_CHECK_TIMEOUT:
        print (f"Checking subsription for {user_id}")
        subscription = await send_unsub_message(user_id, user_data)
    if user_id == ADMIN_ID:
        user_data['banned'] = False
        user_data['subscribed'] = True

    return user_data


# In[12]:


def log_message_history(chat_id, user_id, role_id, message, tokens, timestamp):
    cursor.execute('INSERT INTO chat_history (chat_id, user_id, role_id, message, tokens, timestamp) VALUES (?,?,?,?,?,?)',
                   (chat_id, user_id, role_id, message, tokens, timestamp))
    conn.commit()   
    print (f"Logged {chat_id}: {message}")


# In[13]:


def get_context(chat_id, role_id):
#    cursor.execute('SELECT * FROM chat_history WHERE user_id=?', (user_id,))
    cursor.execute('SELECT * FROM chat_history WHERE chat_id=? AND role_id=? and message NOT LIKE "image: %"', (chat_id, role_id,))
    role_hist = cursor.fetchall()   
    role_hist = role_hist[-CONTEXT_LEN:]
    context = []
    for rec in role_hist:
        context.append(rec['message'])
        if rec['message']=='/clear':
            context = []
    return context


# In[14]:


def add_money_action(user_id, chat_id, amount, desc):
    cursor.execute('INSERT INTO money_acions (user_id, chat_id, description, amount, timestamp) VALUES (?,?,?,?,?)'
        ,(user_id, chat_id, desc, amount, utc()))
    conn.commit()
    minus = ('minus ' if amount<0 else ' ')
    print (f"Added transaction: user {user_id}, chat {chat_id}, {minus}{round(amount,8)} USD: {desc}")


# In[15]:


#def save_user_data(user_id, language , banned, ban_comment,subscribed, balance, sub_checked=None):
def save_user_data(user_data, sub_checked=None):
    cursor.execute('UPDATE user_data SET lang=?, balance=?, banned=?, subscribed=?, ban_comment=? WHERE user_id=?', 
                   (user_data['lang'],round(user_data['balance'],10),user_data['banned'], user_data['subscribed'], user_data['ban_comment'],  user_data['user_id']))
    if sub_checked:
        cursor.execute('UPDATE user_data SET subs_timestamp=? WHERE user_id=?', (utc(), user_data['user_id']))
        print (f"Save sub {user_data['user_id']}: {user_data['subscribed']}")
    conn.commit()    


# In[16]:


async def get_chat_data (chat_id, owner_id=None):
    cursor.execute('SELECT * FROM chat_data WHERE chat_id=?', (chat_id,))
    cd = cursor.fetchone()
    if not cd:
        if not owner_id:
            owner_id = chat_id
        chat = await bot.get_chat(chat_id)
        if chat.id == owner_id:
            title = f"{chat.full_name} (@{chat.username})"
        else:
            title = chat.title
        cursor.execute('INSERT INTO chat_data (chat_id, owner_id, title, role_id, skipped, type) VALUES (?,?,?,?,?,?)'
            ,(chat_id, owner_id, title, 0, 0, chat.type))
        conn.commit()   
#        print ("Added chat to DB")
        print (f"Added chat to DB: {title} ({chat_id}), owner {owner_id}")

        cursor.execute('SELECT * FROM chat_data WHERE chat_id=?', (chat_id,))
        cd = cursor.fetchone()
        if chat.id != owner_id:
            msg = get_message("my_master_is",'eng').format(owner_id)
    elif owner_id and cd['owner_id'] != owner_id:
        cd['owner_id'] = owner_id
        cursor.execute('UPDATE chat_data set owner_id=? where chat_id=?', (owner_id, chat_id,))
        conn.commit()   
        print (f"Updated chat {cd['title']} ({chat_id}) owner to {owner_id}")
        
    return cd


# In[17]:


def upd_chat_counter(chat_id, skipped):
    cursor.execute('UPDATE chat_data set skipped=? WHERE chat_id=?',(skipped, chat_id))
    conn.commit()   
    print (f"Counter skip {chat_id}: {skipped}")


# In[18]:


def get_stat_msg (stats):
    msg = get_message('stats_users', 'rus').format(stats['total_users'], stats['nuser_24'],stats['nuser_7'],stats['nuser_30'])
    n_msg = ""
    for uid, up in stats['moneystat'].items():
        print (uid, up)
        n_msg = f"\n+ {uid}: "
        if up['amount']:
            n_msg += f"оплатил {up['amount']}, "
        if up['referals']:
            n_msg += f"привел {up['referals']}, "
        if up['ref_amount']:
            n_msg += f"они оплатили {up['ref_amount']}."
        msg += n_msg#.strip()
        
    return msg.strip()


# In[19]:


def get_first_message_date():
    all_user = get_all_users_from_db()
    cursor.execute('SELECT * FROM chat_history WHERE user_id=chat_id')
    msg_data = cursor.fetchall()
    minmess = {i:utc() for i in all_user}
    for dataline in msg_data:
        minmess[dataline['chat_id']] = min(dt(dataline['timestamp']), minmess[dataline['chat_id']])
    return minmess


# In[20]:


def get_statistics():
    cursor.execute('SELECT * FROM money_acions where description like "%payment%"')
    pay_data = cursor.fetchall()
    cursor.execute('SELECT * FROM referals')
    refer_data = cursor.fetchall()
    all_user = get_all_users_from_db()
    ret_dict = {'total_users':len(all_user), 'nuser_24':0, 'nuser_7':0, 'nuser_30':0, 'moneystat':{}}
    minmess = get_first_message_date()
        
    for uid, mintime in minmess.items():
        if mintime > utc() - timedelta(days=30):
            ret_dict['nuser_30']+=1
        if mintime > utc() - timedelta(days=7):
            ret_dict['nuser_7']+=1
        if mintime > utc() - timedelta(days=1):
            ret_dict['nuser_24']+=1
            

    moneylist = {}
    for uid in all_user:
        ud = {'amount':0, 'referals':0, 'ref_amount':0}
        for payline in pay_data:
            if payline['user_id']==uid:
                ud['amount'] +=payline['amount']
        if ud['amount'] + ud['referals'] + ud['ref_amount'] >0:
            moneylist[uid]=ud

    for uid in all_user:
        for refline in refer_data:
            if refline['host_id']==uid:
                if uid not in moneylist:
                    moneylist[uid]={'amount':0, 'referals':0, 'ref_amount':0}
                moneylist[uid]['referals'] +=1
                if refline['guest_id'] in moneylist:
                    moneylist[uid]['ref_amount'] += moneylist[refline['guest_id']]['amount']  
                
    ret_dict['moneystat'] = moneylist

    return ret_dict


# In[21]:


def check_add_referal (host_id, guest_id):
    # check if user is not cheating
    allusers = get_all_users_from_db()
    if (host_id==guest_id)  or (host_id not in allusers):
        print (f"Referals: wrong users, no bonus: host {host_id}, guest {guest_id}")
        return False
    minmess = get_first_message_date()
    if (utc() - minmess[guest_id]).total_seconds() > 30:
        print (f"Referals: user {host_id} already known")
        return False

    # check if already used for these users, if not:
    cursor.execute('SELECT * FROM referals')
    refer_pairs = cursor.fetchall()
    for pair in refer_pairs:
        if (pair['host_id']==host_id and pair['guest_id']==guest_id) or (pair['host_id']==guest_id and pair['guest_id']==host_id):
            print (f"Referals: already got bonus before: host {host_id}, guest {guest_id}")
            return False            
    # add record to referals table
    cursor.execute('INSERT INTO referals (host_id, guest_id, timestamp) VALUES (?,?,?)',(host_id, guest_id, utc()))
    conn.commit()    
    print (f"Referals: will pay BONUS: host {host_id}, guest {guest_id}")

    return True

    


# In[22]:


def get_all_users_from_db():
    cursor.execute('SELECT distinct user_id, name from user_data')
    user_data = cursor.fetchall()
    return {i['user_id']:i['name'] for i in user_data}


# In[23]:


def get_all_grout_chats_from_db():
    cursor.execute('SELECT * from chat_data where chat_id != owner_id')
    user_data = cursor.fetchall()
    return {i['chat_id']:i['title'] for i in user_data}


# In[24]:


def get_users_chats(owner_id):
    cursor.execute('SELECT * from chat_data WHERE owner_id=?',(owner_id,))
    userchats = cursor.fetchall()
    return userchats


# In[25]:


def get_banned_users():
    cursor.execute('SELECT * from user_data WHERE banned = 1')
    user_data = cursor.fetchall()
    return {i['user_id']:i['name'] for i in user_data}


# In[26]:


async def send_user_menu(user_id, lang):
    msg = "Menu:"
    reply_markup = InlineKeyboardMarkup()
#    ["🖼 Vision","🖼 Видение"]
#    ["💰 Balance","💰 Баланс"]
#    ["🍖 Shop","🍖 Магазин"]
#    ["🔗 Referal","🔗 Рефелал"]
#    ["📜 Context","📜 Контекст"]
#    ["🧹 Clear","🧹 Очистка"]

    rm = get_role_models()
    for i in rm:
        reply_markup.add(InlineKeyboardButton (text=rm[i]['name'], callback_data=f"model_{i}_{user_id}"))

    reply_markup.add(InlineKeyboardButton (text="--------", callback_data=f"NONE"))
    
    if lang=='eng':
        if (USE_ROLE_MODELS):
            reply_markup.row(InlineKeyboardButton("💬 Groups", callback_data='my_chats'))
        reply_markup.row(InlineKeyboardButton("💰 Balance", callback_data='user_balance'), 
                         InlineKeyboardButton("🔗 Referal", callback_data='get_reflink'),)
        if (USE_SHOP):
            reply_markup.row(InlineKeyboardButton("🍖 Shop", callback_data='show_shop'))
        if (USE_VISION):
            reply_markup.row(InlineKeyboardButton("🖼 Vision", callback_data='get_vision'))
#        reply_markup.row(InlineKeyboardButton("📜 Context", callback_data='get_context'), 
#                         InlineKeyboardButton("🧹 Clear", callback_data='clear_context'),)
    elif lang == 'rus':
        if (USE_ROLE_MODELS):
            reply_markup.row(InlineKeyboardButton("💬 Группы", callback_data='my_chats'))
        reply_markup.row(InlineKeyboardButton("💰 Баланс", callback_data='user_balance'), 
                         InlineKeyboardButton("🔗 Рефелал", callback_data='get_reflink'),)
        if (USE_SHOP):
            reply_markup.row(InlineKeyboardButton("🍖 Магазин", callback_data='show_shop'))
        if (USE_VISION):
            reply_markup.row(InlineKeyboardButton("🖼 Видение", callback_data='get_vision'))
#        reply_markup.row(InlineKeyboardButton("📜 Контекст", callback_data='get_context'), 
#                         InlineKeyboardButton("🧹 Очистка", callback_data='clear_context'),)

    succ = await send_msg (user_id, msg, reply_markup=reply_markup)


# In[27]:


async def send_admin_menu(user_id):
    global currmoney
    msg = get_message('admin_menu_text', 'eng').format(round(currmoney.value,4), RATES_TO_USD)
    reply_markup = InlineKeyboardMarkup()
    reply_markup.row(
                     InlineKeyboardButton("💰 Set Balance", callback_data='set_curr_api_balance'),
                     InlineKeyboardButton("📊 Statistics", callback_data='send_stats'),
                    )
    reply_markup.row(
                     InlineKeyboardButton("📤 Spam users", callback_data='broadcast_users'), 
                     InlineKeyboardButton("🗯 Spam chats", callback_data='broadcast_chats'), 
                    )
    reply_markup.row(InlineKeyboardButton("€ EUR rate", callback_data='rate_eur'), 
                     InlineKeyboardButton("₽ RUB rate", callback_data='rate_rub'),
                    )
    reply_markup.row(InlineKeyboardButton("🔨 BAN", callback_data='ban_users'), 
                     InlineKeyboardButton("⚖️ un-BAN", callback_data='un_ban_users'),
                    )
    reply_markup.row(InlineKeyboardButton("🎁 Gift user money", callback_data='give_user_money'), 
                    )
    
    succ = await send_msg (ADMIN_ID, msg, reply_markup=reply_markup)


# In[28]:


async def send_shop_message(user_data):
    reply_markup = InlineKeyboardMarkup()
    tovary = get_tovary()
    for i in tovary:
        if tovary[i]['active']:
            reply_markup.add(InlineKeyboardButton (text=tovary[i]['title'], callback_data=f"shop_{str(i)}"))
    msg = get_message('shop_text', user_data['lang'])    
    succ = await send_msg (user_data['user_id'], msg, reply_markup=reply_markup)


# In[29]:


async def set_curr_api_balance(message):
    global noted_of_money_shortage
    global currmoney
    try:
        val = float(message.strip())
        currmoney.value = val
        msg = get_message('set_usd_to','eng').format(val)
        succ = await send_msg (ADMIN_ID, msg)
        noted_of_money_shortage = False
    except Exception as e:
        succ = await send_msg (ADMIN_ID, f"Could NOT write current USD balance due to error {str(e)}")


# In[30]:


@dp.callback_query_handler(lambda x: x.data in ['eng', 'rus'])
async def lang_select_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    user_data['lang'] = call.data
    msg = get_message('lang_selected', user_data['lang'])
    save_user_data(user_data)
    succ = await send_msg (user_id, msg)
    await send_user_menu(user_id, user_data['lang'])


# In[31]:


@dp.callback_query_handler(lambda x: x.data == 'give_user_money')
async def give_user_some_money_handler(call, state:FSMContext):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    allusers = get_all_users_from_db()
    userstr = '\n'.join([f"{allusers[i]}: {i}" for i in allusers])#
    msg = get_message('whome_to_gift', user_data['lang']).format(userstr)
    await state.set_state(Form.give_user_money)
    succ = await send_msg (ADMIN_ID, msg)


# In[32]:


@dp.callback_query_handler(lambda x: x.data =='my_chats')
async def my_chats_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reply_markup = InlineKeyboardMarkup()
    msg = get_message('here_are_your_chats', user_data['lang'])
    userchats = get_users_chats(user_id)
    rm = get_role_models()
    for i in userchats:
        if i['chat_id'] == user_id:
            continue
        if i.get('type') =='channel':
            continue
        chat_data = await get_chat_data(i['chat_id'])
        currai = chat_data['role_id']
        ainame = rm[currai]['name']
        btn_text = f"{i['title']} – {ainame}"
        reply_markup.add(InlineKeyboardButton (text=btn_text, callback_data=f"setchat_{i['chat_id']}"))
    succ = await send_msg (user_id, msg, reply_markup=reply_markup)


# In[33]:


@dp.callback_query_handler(lambda x: x.data[:8] =='setchat_')
async def my_chats_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reply_markup = InlineKeyboardMarkup()
    chat_id = int(call.data.split('_')[1])
    chat_data = await get_chat_data(chat_id)
    rm = get_role_models()
    msg = get_message('here_are_rms', user_data['lang']).format(chat_data['title'], chat_id, rm[chat_data['role_id']]['name'])
    for i in rm:
        reply_markup.add(InlineKeyboardButton (text=rm[i]['name'], callback_data=f"model_{str(i)}_{str(chat_id)}"))
    succ = await send_msg (user_id, msg, reply_markup = reply_markup)


# In[34]:


@dp.callback_query_handler(lambda x: x.data =='get_vision')
async def vision_start_handler(call, state:FSMContext):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    if user_data['balance'] < 0 and USE_BALANCE_MONEY and user_id!=ADMIN_ID:
        reflink = f"https://t.me/{me.username}?start={user_id}"
        msg = get_message('limits_out', user_data['lang']).format(REFERAL_INVITATION_BONUS, reflink)
    else:
        await state.set_state(Form.vision_mode)
        msg = get_message('next_vision', user_data['lang'])
    succ = await send_msg (user_id, msg)


# In[35]:


@dp.callback_query_handler(lambda x: x.data =='rate_eur')
async def rate_eur_handler(call, state:FSMContext):
    await state.set_state(Form.set_eur_rate)
    msg = get_message('gimme_eur_rate','eng')
    succ = await send_msg (ADMIN_ID, msg)


# In[36]:


@dp.callback_query_handler(lambda x: x.data =='rate_rub')
async def rate_rub_handler(call, state:FSMContext):
    await state.set_state(Form.set_rub_rate)
    msg = get_message('gimme_rub_rate','eng')
    succ = await send_msg (ADMIN_ID, msg)


# In[37]:


@dp.callback_query_handler(lambda x: x.data =='user_balance')
async def balance_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    msg = get_message('your_balance', user_data['lang']).format(round(user_data['balance'],6))
    succ = await send_msg (user_id, msg)


# In[38]:


@dp.callback_query_handler(lambda x: x.data =='show_shop')
async def show_shop_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    await send_shop_message(user_data)


# In[39]:


@dp.callback_query_handler(lambda x: x.data =='get_reflink')
async def reflink_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reflink = f"https://t.me/{me.username}?start={user_id}"
    msg = get_message('your_reflink', user_data['lang']).format( REFERAL_INVITATION_BONUS,reflink)
    succ = await send_msg (user_id, msg)


# In[40]:


@dp.callback_query_handler(lambda x: x.data =='check')
async def check_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    try: await bot.delete_message (user_id, call.message.message_id)
    except: pass
    await send_unsub_message(user_id, user_data, send_true = True)


# In[41]:


@dp.callback_query_handler(lambda x: x.data =='broadcast_users')
async def broadcast_handler(call, state:FSMContext):
    await state.set_state(Form.broadcast_users)
    msg = get_message(f'gimme_spam_text_for_users', 'eng').format(len(get_all_users_from_db()))
    succ = await send_msg (ADMIN_ID, msg)


# In[42]:


@dp.callback_query_handler(lambda x: x.data =='broadcast_chats')
async def broadcast_handler(call, state:FSMContext):
    spamlen = len(get_all_grout_chats_from_db())
    if spamlen >0:
        await state.set_state(Form.broadcast_chats)
        msg = get_message('gimme_spam_text_for_chats', 'eng').format(spamlen)
    else:
        msg = "Got ZERO chats, nothing to spam."
    succ = await send_msg (ADMIN_ID, msg)


# In[43]:


@dp.callback_query_handler(lambda x: x.data =='set_curr_api_balance')
async def set_curr_api_balance_handler(call, state:FSMContext):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    await state.set_state(Form.state_set_curr_api_balance)
    msg = get_message(f'gimme_curr_balance', 'eng').format(round(currmoney.value,2))
    succ = await send_msg (ADMIN_ID, msg)    


# In[44]:


@dp.callback_query_handler(lambda x: x.data =='send_stats')
async def stats_handler(call):
    stats = get_statistics()
    msg = get_stat_msg(stats)
    succ = await send_msg (ADMIN_ID, msg)    


# In[45]:


@dp.callback_query_handler(lambda x: x.data =='ban_users')
async def ban_handler(call, state:FSMContext):
    await state.set_state(Form.ban_somebody)
    allusers = get_all_users_from_db()
    userstr = '\n'.join([f"{allusers[i]}: {i}" for i in allusers if i not in get_banned_users()])#
    msg = get_message('up_to_ban', 'eng').format(userstr)
    succ = await send_msg (ADMIN_ID, msg)


# In[46]:


@dp.callback_query_handler(lambda x: x.data =='un_ban_users')
async def ubnan_handler (call, state:FSMContext):
    await state.set_state(Form.un_ban_somebody)
    bandict = get_banned_users()
    userstr = '\n'.join([f"{bandict[i]}: {i}" for i in bandict])#
    msg = get_message('up_to_un_ban', 'eng').format(userstr)
    succ = await send_msg (ADMIN_ID, msg)


# In[47]:


@dp.callback_query_handler(lambda x: x.data[:9] == 'checkout_')
async def checkout_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    tovar_id = int(call.data.split("_")[1])
    method_id = int(call.data.split("_")[2])
    await send_invoice (user_id, tovar_id, method_id)


# In[48]:


@dp.callback_query_handler(lambda x: x.data[:9] == 'buy_item_')
async def buy_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reply_markup = InlineKeyboardMarkup()
    tovary = get_tovary()
    tovar_num = int(str(call.data).replace('buy_item_',''))
    tovar = tovary[tovar_num]
    payment_types = {i:PAYMENT_METHODS[i] for i in PAYMENT_METHODS if i != 99}
    if user_id == ADMIN_ID:
        payment_types[99] = PAYMENT_METHODS[99]
    msg = get_message('choose_payment_method', user_data['lang'])
    for po in payment_types:
        reply_markup.add(InlineKeyboardButton(text=payment_types[po]['name'], callback_data=f'checkout_{tovar_num}_{po}'))
    succ = await send_msg (user_id, msg, reply_markup=reply_markup)


# In[49]:


@dp.callback_query_handler(lambda x: x.data[:5] == 'gift_')
async def gift_handler(call):
    tovar_id = int(call.data.split("_")[1])
    user_id = int(call.data.split("_")[2])
    user_data = await get_user_data(user_id)
    tovary = get_tovary()
    amt = tovary[tovar_id]['amount']
    user_data['balance'] += amt
    user_data['banned'] = False
    user_data['subscribed'] = False
    
    save_user_data(user_data)
    
    rec_msg = get_message('you_got_gift', 'eng').format(amt)
    giv_msg = get_message('you_sent_gift', 'eng').format(amt, user_data['name'])
    
    succ = await send_msg (user_id, rec_msg)
    succ = await send_msg (ADMIN_ID, giv_msg)
    
    add_money_action(user_id, ADMIN_ID, amt, f"present: {tovary[tovar_id]['title']}")


# In[50]:


@dp.callback_query_handler(lambda x: x.data[:5] == 'shop_')
async def checkout_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reply_markup = InlineKeyboardMarkup()
    tovary = get_tovary()
    tovar_num = int(str(call.data).replace('shop_',''))
    tovar = tovary[tovar_num]
    desc = tovar['title'] + '\n' + tovar['description']
    reply_markup.add(InlineKeyboardButton(f"BUY", callback_data=f'buy_item_{tovar_num}'))
    succ = await send_msg (user_id, text=desc, photo = tovar['image_url'], reply_markup=reply_markup)


# In[51]:


@dp.callback_query_handler(lambda x: x.data[:6] == 'model_')
async def model_select_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    reply_markup = InlineKeyboardMarkup()
    rm = get_role_models()
    rm_num = int(call.data.split('_')[1])
    chat_id = int(call.data.split('_')[2])
    role = rm[rm_num]
    desc = role['name'] + ' – ' + role['description']
    yesbtn = f"✅ YES!" if user_data['lang']=='eng' else '✅ ДА!'
    backbtn = f"◀️ назад" if user_data['lang']=='eng' else '◀️ назад'
    
    reply_markup.add(InlineKeyboardButton(yesbtn, callback_data=f'actmodel_{rm_num}_{chat_id}'))
    reply_markup.add(InlineKeyboardButton(backbtn, callback_data=f"setchat_{chat_id}"))
    succ = await send_msg (user_id, text=desc, photo = role['image_url'], reply_markup=reply_markup)    


# In[52]:


@dp.callback_query_handler(lambda x: x.data[:9] == 'actmodel_')
async def model_choose_handler(call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    rm = get_role_models()
    rm_num = int(call.data.split('_')[1])
    chat_id = int(call.data.split('_')[2])
    cursor.execute('UPDATE chat_data set role_id=? WHERE chat_id=?',(rm_num, chat_id))
    conn.commit()   
    title = await get_chat_data(chat_id)
    title = title['title']
    msg = get_message('chat_chaged_model', user_data['lang']).format(title, rm[rm_num]['name'])
    succ = await send_msg (user_id, msg)


# In[53]:


@dp.callback_query_handler()
async def inline_callback_btn_click (call):
    user_id = call.from_user.id
    user_data = await get_user_data(user_id)
    if call.data != "NONE":
        print(f"Unknown command: {call.data}")
        


# In[54]:


@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    


# In[55]:


@dp.my_chat_member_handler()
async def added_to_chat(chat_member: types.ChatMemberUpdated):
    global channels_data, me
    global added
    added = chat_member
    if (not me) or (channels_data == None):
        channels_data  = await get_chan_data()
        me = await bot.get_me()

    chat_id = chat_member.chat.id
    user_id = chat_member.from_user.id
    role_models = get_role_models()
    title = chat_member.chat.title
    if chat_member.new_chat_member.user.id == me.id:
        if chat_member.new_chat_member.status in ['kicked', 'left']:
            print (f"I was kicked from chat {chat_id}: {chat_member.chat.title}")
        else:
            owner_id = user_id
            if chat_member.chat.type == 'private':
                title = f"{chat_member.from_user.first_name} {chat_member.from_user.last_name} (@{chat_member.from_user.username})"
                print (f"New LS with user {chat_id}: {title}")
            elif chat_member.chat.type in ['group', 'channel']:
                print (f"I was added to group or channel {chat_id}: {title} in status {chat_member.new_chat_member.status}")
            elif chat_member.chat.type == 'supergroup':
                print (f"I was added to SUPER-GROUP {chat_id}: {title} in status {chat_member.new_chat_member.status}")
                sg = await bot.get_chat(chat_member.chat.id)
                if (sg.linked_chat_id):
                    link_data = await get_chat_data(sg.linked_chat_id)
                    print (f"I was added to linked chat {chat_id}: {title} in status {chat_member.new_chat_member.status}. Linked data:'\n{link_data}'")
                    owner_id = link_data['owner_id']
            else:
                print (f"I was added to {title} ({chat_id})")
                    
            chat_db = await get_chat_data(chat_id, owner_id)
#            cursor.execute('SELECT * FROM chat_data WHERE chat_id=?', (chat_id,))
#            chat_db = cursor.fetchall()#(size=CONTEXT_LEN)    
#            if not (chat_db):
#                cursor.execute('INSERT INTO chat_data (chat_id, owner_id, title, role_id, skipped, type) VALUES (?,?,?,?,?,?)'
#                    ,(chat_id, owner_id, title, 0, 0, chat_member.chat.type))
#                conn.commit()   
                
            if chat_id!=user_id and chat_member.chat.type != 'channel':
                if chat_member.new_chat_member.status != 'administrator' and chat_id!=user_id:
                    msg = get_message('make_me_admin','eng')
                else:
                    msg = get_message('i_am_admin','eng')


# In[56]:


async def ban_user(user_id, comment):
    user_data = await get_user_data(user_id)
    msg = get_message('you_were_banned', 'eng').format(comment)
    user_data['banned'] = True
    user_data['ban_comment'] = comment
    save_user_data(user_data)
    succ = await send_msg (user_id, msg)


# In[57]:


async def unban_user(user_id, comment):
    user_data = await get_user_data(user_id)
    msg = get_message('you_were_unbanned', 'eng').format(comment)
    user_data['banned'] = False
    user_data['ban_comment'] = comment
    save_user_data(user_data)
    succ = await send_msg (user_id, msg)


# In[58]:


async def send_gift_menu(giftuser):
    user_data = await get_user_data(giftuser)
    reply_markup = InlineKeyboardMarkup()
    tovary = get_tovary()
    for i in tovary:
        if tovary[i]['active']:
            reply_markup.add(InlineKeyboardButton (text=tovary[i]['title'], callback_data=f"gift_{i}_{giftuser}"))
    msg = get_message('gift_text', 'eng').format(user_data['name'])
    succ = await send_msg (ADMIN_ID, msg, reply_markup=reply_markup)


# In[59]:


@dp.message_handler(state=Form.give_user_money) # Принимаем состояние
async def gift_handler(message, state: FSMContext):
    await state.finish() # Выключаем состояние
    try:
        giftuser = int(message.text.split()[0].strip())
        if giftuser not in get_all_users_from_db():
            giftuser = 0
    except:
        giftuser = 0
    if (giftuser):
        await send_gift_menu(giftuser)
    else:
        msg = get_message('no_gift', 'eng')        
        succ = await send_msg (ADMIN_ID, msg)


# In[60]:


@dp.message_handler(state=Form.ban_somebody) # Принимаем состояние
async def ban_user_handler(message, state: FSMContext):
    await state.finish() # Выключаем состояние
    try:
        banuser = int(message.text.split()[0].strip())
        if banuser in get_banned_users():
            banuser = 0
    except:
        banuser = 0
    comment = message.text.replace(str(banuser), '').strip()
    if (banuser):
        await ban_user(banuser, comment)
        msg = get_message('user_banned', 'eng').format(banuser)
    else:
        msg = get_message('user_not_banned', 'eng').format(message.text.strip())
    succ = await send_msg (ADMIN_ID, msg)


# In[61]:


@dp.message_handler(state=Form.un_ban_somebody) # Принимаем состояние
async def un_ban_user_handle(message, state: FSMContext):
    await state.finish() # Выключаем состояние  
    try:
        unbanuser = int(message.text.split()[0].strip())
        if unbanuser not in get_banned_users():
            unbanuser = 0
    except:
        unbanuser = 0
    comment = message.text.replace(str(unbanuser), '').strip()
    if (unbanuser):
        await unban_user(unbanuser, comment)
        msg = get_message('user_unbanned', 'eng').format(unbanuser)
    else:
        msg = get_message('user_not_unbanned', 'eng').format(message.text.strip())
    succ = await send_msg (ADMIN_ID, msg)


# In[62]:


@dp.message_handler(state=Form.state_set_curr_api_balance) # Принимаем состояние
async def got_curr_api_balance(message, state: FSMContext):
    await state.finish() # Выключаем состояние    
    await set_curr_api_balance(message.text)


# In[63]:


@dp.message_handler(commands='start')
async def start_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_data = await get_user_data(user_id)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, is_persistent=True)
    markup.add (KeyboardButton('🎹 MENU',))
    if user_id==ADMIN_ID:
        markup.add (KeyboardButton('⚙️ ADMIN MENU'))
    succ = await send_msg (user_id, "Hello there!", reply_markup=markup)

    
    reply_markup = InlineKeyboardMarkup()
    reply_markup.row(InlineKeyboardButton("🇺🇸 English", callback_data='eng'), InlineKeyboardButton("🇷🇺 Русский", callback_data='rus'))
    msg = get_message('select_language','eng') +'\n'+ get_message('select_language','rus')
    succ = await send_msg (message.from_user.id, msg, reply_markup=reply_markup)
    
    if message.text:
        words = message.text.split()
    # check if has invite code, if has:
        if len(words)>=2:
            guest_id = int(message.from_user.id)
            host_id = int (words[1])
            # check and record to referals table if needed
            ref = check_add_referal (host_id, guest_id)
            if (ref):
                # add money to host
                host_user_data = await get_user_data(host_id)
#                host_lang, subsc, balance, tu, banned = await get_user_data(host_id)
                host_user_data['balance'] += REFERAL_INVITATION_BONUS
                save_user_data(host_user_data)
                add_money_action(host_id, guest_id, REFERAL_INVITATION_BONUS, 'referal bonus')
                # send msg to host about this
                msg = get_message('referal_bonus_received', host_user_data['lang']).format(REFERAL_INVITATION_BONUS, round(host_user_data['balance'],6))
                succ = await send_msg (host_id, msg)
                await check_balance_warn()


# In[64]:


@dp.message_handler(content_types=['successful_payment'])
async def got_payment(message):
    user_id = (message.from_user.id)
    user_data = await get_user_data(user_id)
    pmnt = message.successful_payment.to_python()
    tovary = get_tovary()
    tovar = tovary[int(pmnt['invoice_payload'].split('_')[1])]
    user_data['balance'] += tovar['amount']
    msg = get_message('account_added', 'eng').format(tovar['amount'], user_data['balance'])    
    succ = await send_msg (message.chat.id, msg)

    print (f"Got payment:\n{pmnt}")

    # add balance
    save_user_data(user_data)
    # add record to DB payments
    add_money_action(user_id, user_id, tovar['amount'], f'payment: {str(tovar)}')
    # notify admin
    
    userinfo = f"{message.from_user.first_name} {message.from_user.last_name} (@{message.from_user.username}, id {message.from_user.id})"
    adm_msg = get_message('admin_notify_account_added','eng').format(userinfo, tovar['amount'])
    succ = await send_msg (ADMIN_ID, adm_msg)


# In[65]:


@dp.message_handler(commands='my_ids')
async def send_ids(message: types.Message):
    user_id = (message.from_user.id)
    msg = f"Chat id:{message.chat.id}\nYour id: {message.from_user.id}"
    succ = await send_msg (user_id, msg)


# In[66]:


@dp.message_handler(commands='menu')
async def send_user_menu_handler(message: types.Message):
    user_id = (message.from_user.id)
    user_data = await get_user_data(user_id)
    await send_user_menu(user_id, user_data['lang'])


# In[67]:


@dp.message_handler(commands='shop')
async def send_shop(message: types.Message):
    if not USE_SHOP:
        return
    user_id = (message.from_user.id)
    user_data = await get_user_data(user_id)
    await send_shop_message(user_data)


# In[68]:


@dp.message_handler(commands='referal')
async def send_reflink(message: types.Message):
    user_id = (message.from_user.id)
    user_data = await get_user_data(user_id)
    reflink = f"https://t.me/{me.username}?start={user_id}"
    msg = get_message('your_reflink',user_data['lang']).format(REFERAL_INVITATION_BONUS, reflink)
    succ = await send_msg (user_id, msg)


# In[69]:


@dp.message_handler(state=Form.vision_mode) # Принимаем состояние
async def process_vision_request(message, state: FSMContext):
    global currmoney, last_spent
    print (f"VISION MODE!")
    image_size = DEFAULT_IMAGE_MODEL
    user_id = (message.from_user.id)
    user_data = await get_user_data(user_id)
    await state.finish() # Выключаем состояние 
    prompt = message.text

    if (not user_data['subscribed']):
        print (f"{user_id} unsub")
        return    
    if user_data['banned']:
        print (f"{user_id}  banned")
        return    
    
    
    if prompt.lower() == 'cancel' or len(prompt) <10:
        msg = get_message('vision_cancelled',user_data['lang'])
        succ = await send_msg (user_id, msg)
        
        print (f"{user_id} cancelled vision")

        return
        
    if user_data['balance'] < 0 and USE_BALANCE_MONEY and user_id!=ADMIN_ID:
        reflink = f"https://t.me/{me.username}?start={user_id}"
        msg = get_message('limits_out', user_data['lang']).format(REFERAL_INVITATION_BONUS, reflink)
        succ = await send_msg (user_id, msg)
        print (f"{user_id} not enough money for vision")
        return

    msg = get_message('vision_takes_time', user_data['lang'])
    log_message_history(user_id, user_id, 0, f'user_vision: {prompt}', 0, message.date)    
    succ = await send_msg (user_id, msg)

    # generate_image
    vision_url, success = await generate_vision (prompt)
    if not success:
        msg = get_message('ai_vision_error',user_data['lang']) + '\n\n' + vision_url
        succ = await send_msg (user_id, msg)        
    else:
        # send it
        msg = get_message('here_is_your_vision',user_data['lang']).format(me.username)
        succ = await send_msg (user_id, text=msg, photo=vision_url)
        money_used = calc_USD_spent(0,image_size)
        user_data['balance'] -= money_used * TARIF_MODIFICATOR
        save_user_data(user_data)
        log_message_history(user_id,user_id, 0, f'image: {vision_url}', 0, message.date)
        add_money_action(user_id,user_id, - money_used, 'vision')
        currmoney.value -= money_used
        last_spent += money_used
        await check_balance_warn()


# In[70]:


@dp.message_handler(state=Form.broadcast_chats) # Принимаем состояние
async def broadcast_chats_handler(message, state: FSMContext):
    await state.finish()
    if message.text.lower()=='cancel' or len(message.text)<5:
        succ = await send_msg (ADMIN_ID, f"Broadcast CHATS cancelled")
        return
    all_users = get_all_grout_chats_from_db()
    succ = await prospam(message.text, all_users)
    succ2 = await send_msg (ADMIN_ID, f"Broadcast FINISHED for {succ} CHATS")


# In[71]:


@dp.message_handler(state=Form.broadcast_users) # Принимаем состояние
async def broadcast_users_handler(message, state: FSMContext):
    await state.finish()
    if message.text.lower()=='cancel' or len(message.text)<5:
        succ = await send_msg (ADMIN_ID, f"Broadcast USERS cancelled")

        return
    all_users = get_all_users_from_db()
    succ = await prospam(message.text, all_users)
    succ2 = await send_msg (ADMIN_ID, f"Broadcast FINISHED for {succ} USERS")


# In[72]:


@dp.message_handler(state=Form.set_eur_rate) # Принимаем состояние
async def get_eur_rate(message, state: FSMContext):
    await state.finish() # Выключаем состояние    
    try:
        new_rate = round(float(message.text),6)
        RATES_TO_USD['EUR'] = new_rate
        msg = f"EUR rate set to {new_rate}"
    except Exception as e:
        msg = f"Could NOT change EUR rate due to error:\n\n{str(e)}"
    succ = await send_msg (ADMIN_ID, msg)


# In[73]:


@dp.message_handler(state=Form.set_rub_rate) # Принимаем состояние
async def get_rub_rate(message, state: FSMContext):
    await state.finish() # Выключаем состояние    
    try:
        new_rate = round(float(message.text),6)
        RATES_TO_USD['RUB'] = new_rate
        msg = f"RUB rate set to {new_rate}"
    except Exception as e:
        msg = f"Could NOT change RUB rate due to error:\n\n{str(e)}"
    succ = await send_msg (ADMIN_ID, msg)


# In[74]:


def should_bot_answer(message, chat_data, owner_data, req_text):
#    if message.from_user.is_bot:
#        print (f"Message from bot, ignoring ({message.text})")
#        return False
    if message.chat.type =='private':
        return True
    elif message.chat.type =='channel':
        print ("This is a channel, will skip")
        return False
    elif message.chat.type in ['group', 'supergroup']:
        if me.username in req_text:  
            print (f"I was addressed personally, WILL answer")
            return True
        if message.reply_to_message:
            if message.reply_to_message.from_user.username == me.username:
                print (f"I was addressed personally with username, WILL answer")
                return True
            
        if message.from_user.id == 777000:
            if (random.random() * (CHANNEL_ANSWER_FREQUENCY+1) > CHANNEL_ANSWER_FREQUENCY):
                print (f"Received a channel forward to discussion group. Dice RND True!")
                return True
            else:
                print (f"Received a channel forward to discussion group. Dice RND False!")
                return False
        # если сообщение - это форвард с канала в группу обсуждений
        else:
        # если это просто переписка в группе, неважно, при канале или просто:

            if chat_data['skipped'] >= CHAT_ANSWER_FREQUENCY:
                print (f"Current skip counter OK: {chat_data['skipped']} vs congif {CHAT_ANSWER_FREQUENCY}, WILL answer")
                return True
            else:
                print (f"Current skip counter LOW: {chat_data['skipped']} vs congif {CHAT_ANSWER_FREQUENCY}, WILL NOT answer")
                return False
        
    print (f"Chat type {message.chat.type}, No descision, will NOT answer!")
    return False
            
#CHANNEL_ANSWER_FREQUENCY

        # каждый N-й пост нужно комментить (без контеста)


# In[75]:


@dp.message_handler(content_types='any')
async def handle_message(message: types.Message):
    global currmoney, last_spent
    global asd
    asd = message
    if (message.media_group_id):
        print ("I got album!")
    chat_data = await get_chat_data (message.chat.id) #, message.from_user.id)
    owner_id = chat_data['owner_id']
    
    
    if (message.text):
        req_text = str(message.text).strip()
    elif message.caption:
        req_text = str(message.caption).strip()
    else:
        req_text = ''



    if chat_data: 
        role_id = chat_data['role_id']
    else: role_id = 0
    owner_data = await get_user_data(owner_id)
    
    if message.text=="🎹 MENU":
        await send_user_menu(owner_id, owner_data['lang'])
        return
    if message.text=="⚙️ ADMIN MENU" and owner_id == ADMIN_ID:
        await send_admin_menu(ADMIN_ID)
        return

    
    answer = True
    if owner_data['banned'] or not owner_data['subscribed'] :
        answer = False
        print ("Banned or not subscribed!")
    elif owner_data['balance'] < 0 and USE_BALANCE_MONEY and (owner_id != ADMIN_ID):

        print (f"Owner {owner_data} has negative balance!")
        if owner_id==ADMIN_ID:
            print ("But he is admin, WILL answer.")
        else:
            answer = False
            msg = get_message('limits_out', owner_data['lang'])

        
        
    log_message_history(message.chat.id, message.from_user.id, role_id, req_text, 0, message.date)
    context = get_context(message.chat.id, role_id)
    role_prompt = get_role_models()[role_id]['prompt']
    
    if role_id ==-1:
        print ("bot shut down in this chat")
        return
    if req_text =='':
        print ("blank message, ignoring it")
        return
    


    chat_answer = should_bot_answer(message, chat_data, owner_data, req_text)
            
    if chat_answer and answer:
        trim_cont = trim_context("\n".join(context))
        if message.from_user.id == 777000:
            trim_cont = ''
        if len (req_text)>1:
            wait_msg = get_message('processing', owner_data['lang'])
            wait_msg_tg = await send_msg (message.chat.id, text=wait_msg, reply_to_message_id = message.message_id)
            query = f"{role_prompt}:\n\n{trim_cont}\n\n{req_text}###".strip()
            msg, add_tokens, success = await get_openai_response (query)
            await bot.delete_message (message.chat.id, wait_msg_tg.message_id)
            if (success) and msg.strip():
                log_message_history(message.chat.id, me.id, role_id, msg, add_tokens, utc())
                balance_used = calc_USD_spent(add_tokens)
                currmoney.value -= balance_used
                last_spent += balance_used
                add_money_action(owner_id, message.chat.id, - balance_used * TARIF_MODIFICATOR, 'GPT usage')
                owner_data['balance'] = owner_data['balance'] - balance_used * TARIF_MODIFICATOR            
                save_user_data(owner_data)
                chat_data['skipped'] = 0
                upd_chat_counter(message.chat.id, 0)
                succ = await send_msg (message.chat.id, text=msg, reply_to_message_id = message.message_id)
                
            else:
                print (f"Got error from OpenAI, or it rerurned NO message: '{msg}'")
        else:
            print (f"Input message too short, will NOT answer.")
#        print (f"{success}: ({add_tokens} tokens), chat_answer {chat_answer}, answer {answer}. context: {context}\ntrim:{trim_cont}\nrole_prompt:{role_prompt}\nmessage={message.text}\nMSG:{msg}")
    else:
        upd_chat_counter(message.chat.id, chat_data['skipped'] +1)

# Start the Bot
if __name__ == '__main__':
    print(f"Bot started!")
    executor.start_polling(dp, skip_updates=True)
# ====== END =====
# In[ ]:

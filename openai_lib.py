import openai
import tiktoken
from bot_config import *
from datetime import datetime, timedelta


# Init OpenAI
openai.api_key = openai_key
encoding = tiktoken.get_encoding('gpt2')


def calc_USD_spent (tokens_spent, model=DEFAULT_TEXT_MODEL):
    if model[:3] =='img':
        return AI_MODELS[model]['ktoken_price']
    else:
        if model not in AI_MODELS:
            model = DEFAULT_MODEL
        return tokens_spent / 1000 * AI_MODELS[model]['ktoken_price']
    

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
    except Exception as e:
        resp = (f"OpenAI error:\n{str(e)}")
        token_used = 0
    return resp, token_used


async def get_openai_response2 (role_prompt, context, msg):
    msg_list = [{'role':'system','content': role_prompt}, *context, {'role':'user', 'content':msg}]
#    print (msg_list)
    req_tokens = 0
    for i in msg_list:
        req_tokens +=3
        req_tokens += estimate_token_count(i['content'])
    max_tokens = min(max(4095 - CONTIGENCY - req_tokens, 200), 4095 - CONTIGENCY)
    
    try:
        resp = await openai.ChatCompletion.acreate(
          model="gpt-3.5-turbo",
          max_tokens=max_tokens,
          messages=msg_list,
          n=1,
          stop="###",
          temperature=TEMPERATURE
        )
        token_used = int(resp["usage"]["total_tokens"] )
        resp = str(resp.choices[0].message['content']).strip()
    except Exception as e:
        resp = (f"OpenAI error:\n{str(e)}")
        token_used = 0
    return resp, token_used



def estimate_token_count(string: str, encoding_name = "gpt2") -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


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


print(f"OpenAI & tokenizer initiated ({DEFAULT_TEXT_MODEL})!")
import openai
import tiktoken
from bot_config import *
from datetime import datetime, timedelta


# Init OpenAI
openai.api_key = openai_key
encoding = tiktoken.get_encoding('gpt2')


def calc_USD_spent (tokens_complete, tokens_context=0, model=DEFAULT_TEXT_MODEL):
    if model[:3] =='img':
        return AI_MODELS[model]['image_price']
    else:
        if model not in AI_MODELS:
            model = DEFAULT_MODEL
        if 'ktoken_price_context' not in AI_MODELS[model].keys():
            AI_MODELS[model]['ktoken_price_context'] = AI_MODELS[model]['ktoken_price_complete']
        total_spent = tokens_complete / 1000 * AI_MODELS[model]['ktoken_price_complete'] + tokens_context / 1000 * AI_MODELS[model]['ktoken_price_context']
        return round(total_spent,10)
    

async def get_openai_response3 (role_prompt, context, msg, model=DEFAULT_TEXT_MODEL):
    msg_list = [{'role':'system','content': role_prompt}, *context, {'role':'user', 'content':msg}]
#    print (msg_list)
    req_tokens = 0
    for i in msg_list:
        req_tokens +=3
        req_tokens += estimate_token_count(i['content'])
    model_token_limit = AI_MODELS[model]['maxtokens'] - CONTIGENCY
    max_tokens = min(model_token_limit - req_tokens, model_token_limit)
    
    try:
        resp = await openai.ChatCompletion.acreate(
          model=model,
          max_tokens=max_tokens,
          messages=msg_list,
          n=1,
          stop="###",
          temperature=TEMPERATURE
        )
        ct = int(resp["usage"]['completion_tokens'])
        pt = int(resp["usage"]['prompt_tokens'])
        resp = str(resp.choices[0].message['content']).strip()
    except Exception as e:
        resp = (f"OpenAI error:\n{str(e)}")
        pt = 0
        ct = 0
    return resp, ct, pt



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
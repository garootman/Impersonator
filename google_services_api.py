from bot_config import *
import os


from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials



os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_API_KEY_FILE



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


translate_service = get_translate_service()
print (f"Google translate services initiated!")
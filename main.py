import datetime
from collect import CollectResults
from sender import Sender
import dotenv
import os
import time

dotenv.load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")

while True:

    print("Iniciando processo...")

    print('Coletando dados do ano atual...')
    collect_data = CollectResults(years = range(2020, 2027))
    collect_data.process_years()

    print('Enviando dados...')
    sender_data = Sender(bucket_name=BUCKET_NAME, bucket_folder='f1/results')
    sender_data.process_folder('data/')
    
    print("Processo finalizado. Aguardando 6 horas para a próxima execução...")
    time.sleep(60 * 60 * 6)  # Sleep for 6 hours
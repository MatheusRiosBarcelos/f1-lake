#%%

import fastf1
import pandas as pd
pd.set_option('display.max_columns', None)

# %%

for i in range(1, 50):

    print(f"Coletando GP {i:02}...")
    
    # Define a sessão de busca e carrega os dados
    try:
        session = fastf1.get_session(2021, i, 'R')
    
    except ValueError as err:
        print(err)
        break

    session._load_drivers_results()
    
    # Exibe e salva os dados obtidos
    session.results
    session.results.to_parquet(f"data/2021_{i:02}_R.parquet")

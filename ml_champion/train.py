# %%

import pandas as pd
from sklearn import model_selection

# %%

df = pd.read_csv('../data/abt_f1_drivers_champion.csv', sep=';')
df.head()

# %%

df['year'] = df['dt_ref_life'].apply(lambda x: x.split('-')[0])

df_driver_year = df[['driverid_life', 'year', 'flChampion']].drop_duplicates()
df_driver_year.sort_values(['driverid_life', 'year'], ascending=[True,False])

train, test = model_selection.train_test_split(
    df_driver_year,
    random_state=42,
    train_size=0.8,
    stratify=df_driver_year['flChampion'] 
)

print("Taxa de campeões treino", train['flChampion'].mean())
print("Taxa de campeões teste", test['flChampion'].mean())

# %%

df_train = train.merge(df)
df_test = test.merge(df)

print("Quantidade de linhas train:", df_train.shape)
print("Quantidade de linhas test:", df_test.shape)

# %%

features = df_train.columns[4:]
features

X_train, y_train  = df_train[features], df_train['flChampion']
X_test, y_test  = df_test[features], df_test['flChampion']

# %%



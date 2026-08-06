#%%

from pyexpat import features

import flask
import mlflow
import pandas as pd

mlflow.set_tracking_uri("http://127.0.0.1:5000")

#%%

results = mlflow.search_registered_models(filter_string="name='f1_driver_champion'")
if not results:
    raise ValueError("No registered model found with name 'f1_driver_champion'")
model = results[-1]
last_version = max(int(v.version) for v in model.latest_versions)
MODEL = mlflow.sklearn.load_model(f"models:/f1_driver_champion/{last_version}")

#%%

app = flask.Flask(__name__)

@app.route('/health_check')
def health_check():
    return "OK", 200

@app.route('/predict', methods=['POST'])
def predict():
    payload = flask.request.get_json()
    data = payload.get('data', [])
    if len(data) == 0:
        return {'error': 'No features provided'}, 400

    df = pd.DataFrame(data)
    X = df[MODEL.feature_names_in_]
    proba = MODEL.predict_proba(X)[:, 1]
    
    df['proba'] = proba
    payload = df[['id', 'proba']].to_dict(orient='records')
    
    return {'data': payload}, 200

if __name__ == '__main__':
    app.run(host='localhost', port=4040)
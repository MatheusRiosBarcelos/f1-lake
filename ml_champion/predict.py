# %%

import requests

resp = requests.get("http://localhost:4040/health_check")
print(resp.status_code)
print(resp.text)
# %%

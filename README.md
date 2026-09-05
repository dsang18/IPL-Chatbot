Download the dataset from kaggle - https://www.kaggle.com/code/arbazkhan971/indian-premier-league-analysis-2008-2025/input
<br>
Save the IPL.csv file inside data folder in the same directory.

## Backend API

Install the dependencies, then start the FastAPI server:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload
```

Use `POST /api/chat/stream` with `{ "message": "..." }`. The endpoint emits
server-sent events named `progress`, followed by either `complete` or `error`.
The final public result includes only KPIs, insights, and visualization data;
generated SQL remains on the server.

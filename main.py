from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="Prince of Gold AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MY_USDT_WALLET = "TPixXPpdAUCXLMxgZgfvrzZLJxb3V94E9n"
active_bots = {}

class BotRequest(BaseModel):
    user_id: str
    broker: str
    server: str
    login: int
    password: str
    account_type: str = "DEMO"
    lot_size: float = 0.01

class PaymentVerifyRequest(BaseModel):
    user_id: str
    txid: str
    expected_amount: float

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Prince of Gold AI v1.0",
        "wallet": MY_USDT_WALLET
    }

@app.post("/start-bot")
def start_bot(req: BotRequest):
    active_bots[req.user_id] = {
        "status": "RUNNING",
        "broker": req.broker,
        "server": req.server,
        "login": req.login,
        "account_type": req.account_type
    }
    return {"message": f"Bot started on {req.server}", "status": "RUNNING"}

@app.post("/stop-bot/{user_id}")
def stop_bot(user_id: str):
    if user_id in active_bots:
        active_bots[user_id]["status"] = "STOPPED"
    return {"message": "Bot stopped safely", "status": "STOPPED"}

@app.get("/bot-status/{user_id}")
def get_bot_status(user_id: str):
    return active_bots.get(user_id, {"status": "STOPPED"})

@app.post("/verify-usdt")
def verify_usdt_trc20(req: PaymentVerifyRequest):
    url = f"https://trongrid.io{req.txid}/events"
    res = requests.get(url).json()
    if "data" in res and len(res["data"]) > 0:
        for event in res["data"]:
            result = event.get("result", {})
            amount = float(result.get("value", 0)) / 1_000_000
            if amount >= req.expected_amount:
                return {"verified": True, "amount_paid": amount, "status": "UNLOCKED"}
    raise HTTPException(status_code=400, detail="Transaction not confirmed or invalid amount.")

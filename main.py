from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests

app = FastAPI(title="Prince of Gold AI Engine v2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MY_USDT_WALLET = "TPixXPpdAUCXLMxgZgfvrzZLJxb3V94E9n"
API_SECRET_KEY = "PRINCE_GOLD_2026_SECURE"

active_bots = {}
trader_stats = {}

class BotRequest(BaseModel):
    user_id: str
    broker: str
    server: str
    login: int
    password: str
    account_type: str = "DEMO"
    lot_size: float = 0.01

class ProfitReportRequest(BaseModel):
    user_id: str
    profit_change: float
    account_type: str = "DEMO"

class PaymentVerifyRequest(BaseModel):
    user_id: str
    txid: str
    expected_amount: float

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Prince of Gold AI v2.0",
        "wallet": MY_USDT_WALLET
    }

@app.post("/start-bot")
def start_bot(req: BotRequest, x_api_key: Optional[str] = Header(None)):
    stats = trader_stats.get(req.user_id, {"net_profit": 0.0, "commission_due": 0.0})
    if req.account_type == "REAL" and stats["commission_due"] >= 10.0:
        raise HTTPException(status_code=402, detail="Commission limit ($10) reached. Pay via USDT TRC-20 to unlock.")
        
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
    bot = active_bots.get(user_id, {"status": "STOPPED"})
    stats = trader_stats.get(user_id, {"net_profit": 0.0, "commission_due": 0.0})
    return {**bot, **stats}

@app.post("/report-profit")
def report_profit(req: ProfitReportRequest):
    if req.user_id not in trader_stats:
        trader_stats[req.user_id] = {"net_profit": 0.0, "commission_due": 0.0}
        
    trader_stats[req.user_id]["net_profit"] += req.profit_change
    net = trader_stats[req.user_id]["net_profit"]
    
    # High-Water Mark: Komishinii 25% bu'aa qulqulluu (Net Profit > 0) qofa irratti herrega
    if req.account_type == "REAL" and net > 0:
        trader_stats[req.user_id]["commission_due"] = round(net * 0.25, 2)
    else:
        trader_stats[req.user_id]["commission_due"] = 0.0
        
    # Yoo komishiniin $10 ga'e ofiin dhaaba
    if trader_stats[req.user_id]["commission_due"] >= 10.0 and req.user_id in active_bots:
        active_bots[req.user_id]["status"] = "PAUSED_UNPAID"
        
    return trader_stats[req.user_id]

@app.post("/verify-usdt")
def verify_usdt_trc20(req: PaymentVerifyRequest):
    try:
        url = f"https://trongrid.io{req.txid.strip()}/events"
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="Transaction not found. Please check your TxID and try again.")
            
        data = res.json()
        if "data" in data and len(data["data"]) > 0:
            for event in data["data"]:
                result = event.get("result", {})
                amount = float(result.get("value", 0)) / 1_000_000
                if amount >= req.expected_amount:
                    if req.user_id in trader_stats:
                        trader_stats[req.user_id]["commission_due"] = 0.0
                    if req.user_id in active_bots and active_bots[req.user_id]["status"] == "PAUSED_UNPAID":
                        active_bots[req.user_id]["status"] = "RUNNING"
                    return {"verified": True, "amount_paid": amount, "status": "UNLOCKED"}
                    
        raise HTTPException(status_code=404, detail="Transaction not found or insufficient USDT amount. Try again.")
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=404, detail="Transaction not found. Please verify your TxID and try again.")

# 🚀 Binance Futures Testnet Trading Bot

A production-ready **Python CLI application** to place and manage orders on **Binance Futures Testnet (USDT-M)**.

---

## ⚙️ Setup

```bash
git clone <your-repo-link>
cd trading_bot
pip install -r requirements.txt
```

---

## 🔑 API Setup

1. Go to https://testnet.binancefuture.com  
2. Login and create API Key  
3. Create a `.env` file in root directory:

```.env
BINANCE_TESTNET_API_KEY=your_api_key
BINANCE_TESTNET_API_SECRET=your_api_secret

## 🖥️ Usage

### 🔹 Check API
```bash
python cli.py ping
```

### 🔹 Place Orders

```bash
# MARKET
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# LIMIT
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 90000

# STOP MARKET
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000
```

### 🔹 Other Commands

```bash
python cli.py account          # Account info
python cli.py orders           # Open orders
python cli.py cancel --symbol BTCUSDT --order-id <id>
```

---

## 📦 Features

- Supports **MARKET, LIMIT, STOP_MARKET** orders  
- Secure API handling using `.env`  
- Structured logging (file + console)  
- Strong error handling (API, validation, network)  
- Clean CLI interface using `argparse`  

---

## 📁 Project Structure

```
trading_bot/
├── bot/
├── cli.py
├── logs/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🛠 Tech Stack

- Python 3  
- requests  
- python-dotenv  
- Binance Futures REST API  

---

## ⚠️ Notes

- Works on **Binance Futures Testnet (USDT-M only)**  
- API keys are not included for security reasons  
- Use correct quantity precision (e.g. 0.001 BTC)

---

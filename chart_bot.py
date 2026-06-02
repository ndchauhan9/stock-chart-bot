import os
import requests
import yfinance as yf
import mplfinance as mpf
import gspread

from datetime import datetime
from google.oauth2.service_account import Credentials

# =========================
# Google Credentials
# =========================

with open("credentials.json", "w") as f:
    f.write(os.environ["GOOGLE_CREDENTIALS"])

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)

gc = gspread.authorize(creds)

# =========================
# Read Sheet
# =========================

sheet = gc.open("Stock charts - Bullish").sheet1
stocks = sheet.col_values(1)[1:]

print("Stocks Found:", stocks)

# =========================
# Telegram
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# =========================
# Charts Folder
# =========================

os.makedirs("charts", exist_ok=True)

# =========================
# Process Stocks
# =========================

for s in stocks:

    try:

        stock = s + ".NS"

        print(f"Processing {stock}")

        df = yf.download(
            stock,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            print(f"No data for {s}")
            continue

        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        # =========================
        # 52 Week High Anchored Avg
        # =========================

        high_date = df["High"].idxmax()

        anchor_df = df.loc[high_date:].copy()

        anchor_df["Anchored_Avg"] = (
            anchor_df["Close"]
            .expanding()
            .mean()
        )

        df["Anchored_Avg"] = anchor_df["Anchored_Avg"]

        # =========================
        # DMAs
        # =========================

        df["DMA20"] = df["Close"].rolling(20).mean()
        df["DMA50"] = df["Close"].rolling(50).mean()
        df["DMA200"] = df["Close"].rolling(200).mean()

        apds = [

            mpf.make_addplot(
                df["DMA20"],
                color="yellow",
                width=1.5
            ),

            mpf.make_addplot(
                df["DMA50"],
                color="blue",
                width=1.5
            ),

            mpf.make_addplot(
                df["DMA200"],
                color="red",
                width=2
            ),

            mpf.make_addplot(
                df["Anchored_Avg"],
                color="grey",
                width=2.5
            )
        ]

        # =========================
        # Date Format
        # =========================

        chart_date = (
            f"{datetime.now().day} "
            f"{datetime.now().strftime('%b %y').lower()}"
        )

        # =========================
        # Save Chart
        # =========================

        filename = f"charts/{s}.png"

        mpf.plot(
            df,
            type="candle",
            style="yahoo",
            volume=True,
            addplot=apds,
            figsize=(15, 8),
            title=f"{s} | {chart_date}",
            savefig=filename
        )

        # =========================
        # Telegram
        # =========================

        with open(filename, "rb") as photo:

            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": f"{s} | {chart_date}"
                },
                files={
                    "photo": photo
                }
            )

            print(f"Telegram Response for {s}")
            print(response.text)

        print(f"Sent: {s}")

    except Exception as e:

        print(f"Error in {s}: {e}")

print("Completed Successfully")

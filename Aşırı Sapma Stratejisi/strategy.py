#pip install ta
#pip install ccxt

from ta.trend import SMAIndicator
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
import config
import pandas as pd
import warnings
import ccxt
from smtplib import SMTP
import winsound
import time
duration = 1000  # milliseconds
freq = 440  # Hz
warnings.filterwarnings("ignore")

# SETTİNGS
symbolName = input("Sembol Girin (BTC, ETH, LTC...vb): ").upper()
islemeGirecekPara = input("Toplam Paranın Yüzde Kaçıyla İşleme Girsin (25, 50, 100...vb): ")
symbol = symbolName+"/USDT"
leverage = input("Kaldıraç Büyüklüğü: ")
stopLoss = input("StopLoss %: ")
MaType = input("MA Tipi (SMA, EMA):" ).lower()
MaValue = input("MA Değeri: ")

pozisyondami = False
islemSayisi = 0
win = 0
loss = 0
winRate = 0
longEnterZaman = 0
sayac = 0

# API CONNECT
exchange = ccxt.binance({
"apiKey": config.apiKey,
"secret": config.secretKey,

'options': {
'defaultType': 'future'
},
'enableRateLimit': True
})

while True:
    try:
        balance = exchange.fetch_balance()
        free_balance = exchange.fetch_free_balance()
        positions = balance['info']['positions']
        newSymbol = symbolName+"USDT"
        current_positions = [position for position in positions if float(position['positionAmt']) != 0 and position['symbol'] == newSymbol]
        position_bilgi = pd.DataFrame(current_positions, columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet", "positionAmt", "positionSide"])
        
        #Pozisyonda olup olmadığını kontrol etme
        if not position_bilgi.empty and float(position_bilgi["positionAmt"][len(position_bilgi.index) - 1]) != 0:
            pozisyondami = True
        else: pozisyondami = False
        
        # Long pozisyonda mı?
        if not position_bilgi.empty and float(position_bilgi["positionAmt"][len(position_bilgi.index) - 1]) > 0:
            longPozisyonda = True
        else: longPozisyonda = False

        
        # LOAD BARS
        bars = exchange.fetch_ohlcv(symbol, timeframe="1m", since = None, limit = 1500)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # LOAD MA
        if MaType == "ema":
            Ema = EMAIndicator(df["close"], float(MaValue))
            df["MA"] = Ema.ema_indicator()
        if MaType == "sma":
            Sma= SMAIndicator(df["close"], float(MaValue))
            df["MA"] = Sma.sma_indicator()

        # LOAD RSI
        rsi = RSIIndicator(df["close"], 14)
        df["rsi"] = rsi.rsi()
        
        # LONG ENTER
        def longEnter(alinacak_miktar):
            order = exchange.create_market_buy_order(symbol, alinacak_miktar)
            winsound.Beep(freq, duration)
            
        # LONG EXIT
        def longExit():
            order = exchange.create_market_sell_order(symbol, float(position_bilgi["positionAmt"][len(position_bilgi.index) - 1]), {"reduceOnly": True})
            winsound.Beep(freq, duration)
        
        # BULL EVENT
        if longPozisyonda == False and float(df["rsi"][len(df.index)-2]) <= 10  and df["close"][len(df.index)-2] < df["MA"][len(df.index)-2]:
            alinacak_miktar = (((float(free_balance["USDT"]) / 100 ) * float(islemeGirecekPara)) * float(leverage)) / float(df["close"][len(df.index) - 1])
            print("LONG İŞLEME GİRİLİYOR...")
            longEnter(alinacak_miktar)
            longEnterZaman = df["timestamp"][len(df.index)-1]
            baslik = symbol
            message = "LONG ENTER\n" + "Toplam Para: " + str(balance['total']["USDT"])
            content = f"Subject: {baslik}\n\n{message}"
            mail = SMTP("smtp.gmail.com", 587)
            mail.ehlo()
            mail.starttls()
            mail.login(config.mailAddress, config.password)
            mail.sendmail(config.mailAddress, config.sendTo, content.encode("utf-8"))

        # STOP LOSS
        if longPozisyonda and ((float(df["close"][len(df.index)-1]) - float(position_bilgi["entryPrice"][len(position_bilgi.index) - 1])) / float(position_bilgi["entryPrice"][len(position_bilgi.index) - 1])) * 100 * -1 >= float(stopLoss):
            print ("LONG İŞLEMDEN KAR İLE ÇIKILIYOR...")
            longExit()
            baslik = symbol
            message = "LONG EXIT (STOP LOSS)\n" + "Toplam Para: " + str(balance['total']["USDT"])
            content = f"Subject: {baslik}\n\n{message}"
            mail = SMTP("smtp.gmail.com", 587)
            mail.ehlo()
            mail.starttls()
            mail.login(config.mailAddress, config.password)
            mail.sendmail(config.mailAddress, config.sendTo, content.encode("utf-8")) 
        
        # TAKE PROFIT
        if longPozisyonda and df["high"][len(df.index)-1] >= df["MA"][len(df.index)-2] and df["timestamp"][len(df.index)-1] != longEnterZaman:
            print ("LONG İŞLEMDEN KAR İLE ÇIKILIYOR...")
            longExit()
            baslik = symbol
            message = "LONG EXIT (TAKE PROFIT)\n" + "Toplam Para: " + str(balance['total']["USDT"])
            content = f"Subject: {baslik}\n\n{message}"
            mail = SMTP("smtp.gmail.com", 587)
            mail.ehlo()
            mail.starttls()
            mail.login(config.mailAddress, config.password)
            mail.sendmail(config.mailAddress, config.sendTo, content.encode("utf-8"))
 
        if pozisyondami == False:
            print("POZİSYON ARANIYOR...")
        if longPozisyonda:
            print("LONG POZİSYONDA BEKLİYOR")

        time.sleep(2)
        
    except ccxt.BaseError as Error:
        print ("[ERROR] ", Error )
        continue
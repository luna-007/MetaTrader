#Importing the necessary libararies
import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime as dt
from colorama import Back

#setting variables which will be used 
symbol = 'EURUSD'
volume = float(10)
short_filter = 'sma'
long_filter = '52_sma'
filter_by = 13
sec_filter = 52
sleep = 60

#Establishing connection with the Terminal
if not mt5.initialize():
    print("Not able to initialize")
    quit()

# print(mt5.account_info())

#Get all the open positions
# positions = mt5.positions_get()

"""
Functions
"""

def order_status(order):
    if len(order) != 0:
        if order[7] == 'Requote':
            try:
                print(Back.YELLOW + "Trying with increased deviation")
                ticket, volume = get_ticket_data()
                close_position(symbol, ticket, volume, 10)
            except Exception as e:
                print(Back.RED + "Executed Try and Error")
                print(Back.RED + "Reason For Error: ", order[7])
                raise SystemExit(0)
        elif order[7] == 'Request executed':
            print(Back.GREEN + "Check Performed and No Errors Found")
    else:
        print(Back.BLUE + "Checking Execution: ", order)


#Function to figure out if the positions or short or long positions
def position_type():
    positions = mt5.positions_get()
    try:
        positions = positions[0][5]
        if positions == 1:
            short_pos = True
            long_pos = False
        elif positions == 0:
            long_pos = True
            short_pos = False
        else:
            return False, False
    except:
        positions = -1
        long_pos = False
        short_pos = False
        return long_pos, short_pos

    return long_pos, short_pos

#Getting the Order Number and the position size
def get_ticket_data():
    positions = mt5.positions_get()
    if len(positions) != 0:
        return positions[0][0], positions[0][9], positions[0][10]
    else: 
        print(Back.YELLOW + "No open Positions to get ticket from ") 
        return 0, 0
    

#Getting historical data and generating indicators etc.
def train_data():

    # To Generate Signals from a different timeframe and implement it on a different one

    # signal = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
    # signal_frame = pd.DataFrame(signal)
    # signal_frame['time'] = pd.to_datetime(signal_frame['time'], unit='s')
    # signal_frame.drop(['spread', 'real_volume'], axis=1, inplace=True)
    # signal_frame['ema'] = rates_frame['close'].ewm(span=filter_by).mean()
    # signal_frame['sma'] = rates_frame['close'].rolling(filter_by).mean()
    # print(signal_frame.iloc[-1][['sma', 'ema']])


    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
    rates_frame = pd.DataFrame(rates)
    rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
    rates_frame.drop(['spread', 'real_volume'], axis=1, inplace=True)
    rates_frame[short_filter] = rates_frame['close'].rolling(filter_by).mean()
    rates_frame[long_filter] = rates_frame['close'].rolling(sec_filter).mean()
    rates_frame['ema'] = rates_frame['close'].ewm(filter_by).mean()
    print(Back.BLUE + f'{rates_frame.iloc[-1][[long_filter, short_filter, "close"]]}')
    return rates_frame

def get_final_pos(order):

    if len(order) != 0:

        ticket = order[1]
        pos_details = mt5.history_deals_get(ticket=ticket)
        order_type = pos_details[0][4]
        price = pos_details[0][10]
        volume = pos_details[0][9]
        current_price = mt5.symbol_info_tick(symbol)
        if order_type == 1:
            current_price = current_price.bid
            profit = (price - current_price) * volume
            print(dt.now(), Back.RED + "The Current Short Position is: ", profit)
        elif order_type == 0:
            current_price = current_price.ask
            profit = (price - current_price) * volume 
            print(dt.now(), Back.GREEN + "The Current Long Position is: ", profit)
        else:
            print(Back.RED + "Some Error In Calculating current Position")

        return price

    elif len(order) == 0:
        
        try:
            open_pos = mt5.positions_get(symbol=symbol)
            profit = open_pos[0][15]
            pos_type = open_pos[0][5]
            if pos_type == 0:
                print(Back.GREEN + "EXISTING:  The Current Long Position is: ", profit)
            elif pos_type == 1:
                print(Back.RED + "EXISTING:  The Current Short Position is: ", profit)
        except Exception as e:
            print(Back.YELLOW + "No Open Positions")

        return profit

#Function for sending buy orders
def buy_order(symbol):

    price = mt5.symbol_info_tick(symbol).ask
    buy_price = float(price)

    """
    buy price is not the same as tick data, got an error
    """

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": float(buy_price - (buy_price * 0.00040)),
        "tp": float(buy_price + (buy_price * 0.00045)),
        "deviation" : 5,
        "comment": "Buy Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN
    }

    order = mt5.order_send(request)
    order_status(order)
    # print(order)
    print('Checking if go Long Order was sent: ', order[7])
    return order

#Function for sending sell orders
def sell_order(symbol):

    price = mt5.symbol_info_tick(symbol).bid
    sell_price = float(price)
    print("First check: ", sell_price)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": float(sell_price + (sell_price * 0.00030)),
        "tp": float(sell_price - (sell_price * 0.00045)),
        "deviation": 5,
        "comment": "Sell Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN
    }

    order = mt5.order_send(request)
    order_status(order)
    print('Checking if go Short Order was sent: ', order[7])
    return order

#Function to close any open positions when the trend changes
def close_position(enter, ticket, volume, entry_price, deviation=5):

    long_pos, short_pos = position_type()

    if (long_pos == True):

        price = mt5.symbol_info_tick(enter).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": enter,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation" : deviation,
            "comment": "Closing Long",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
            "position": ticket
        }

        buy_ = mt5.order_send(request)
        order_status(buy_)
        close_bal(volume, entry_price, price, True)
        print(Back.CYAN + "Checking If Long Close Order Executed: ", buy_[7])
        return buy_
    
    elif (short_pos == True):

        price = mt5.symbol_info_tick(enter).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": enter,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "deviation" : deviation,
            "comment": "Closing Short",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
            "position": ticket
        }

        sell_ = mt5.order_send(request)
        order_status(sell_)
        close_bal(volume, entry_price, price, False)
        print(Back.CYAN + "Checking If Short close Order Executed: ", sell_[7])
        return sell_
    
def close_bal(volume, entry_price, price, type):

    if type:
        net_pos = (price - entry_price) * volume * 100000
        print(Back.YELLOW + "Last Closed Long Position: ", round(net_pos, 2))
    else:
        net_pos = (entry_price - price) * volume * 100000
        print(Back.YELLOW + "Last closed Short Position: ", round(net_pos, 2))

#Execution Function which sends orders based on the signals generated
def main(short_filter, long_filter):

    pos = ()
    while True:
        
        long_pos, short_pos = position_type()
        ticket, volume, entry_price = get_ticket_data()
        price_data = train_data()
        get_final_pos(pos)

        #Long Position Trigger
        if price_data[short_filter].iloc[-1] > price_data[long_filter].iloc[-1]:
            # print('Crossover: Long Position should Initiate')
            print(Back.GREEN + "Crossover: 13MA is higher is than 52MA")
            print(Back.GREEN + "Go LONG")
            if long_pos == False and short_pos == True:
                pos = close_position(symbol, ticket, volume, entry_price) #Entry Price is added for profit/loss calculation
                pos = buy_order(symbol)
                long_pos = True
                short_pos = False
                print(dt.now(),Back.GREEN + ' Short Position Exited and Long Position Initiated')
            elif long_pos == False and short_pos == False:
                pos = buy_order(symbol)
                long_pos = True
                print(dt.now(),Back.GREEN + ' No Existing Short Position, Initiated a long')
            elif short_pos == True:
                pos = close_position(symbol, ticket, volume, entry_price)
                short_pos = False
                print(dt.now()," Open Short position closed as trend changed")
            elif long_pos == True:
                print(dt.now(),Back.GREEN + " Long: Already with the trend")

        #Short Position Trigger
        elif price_data[long_filter].iloc[-1] > price_data[short_filter].iloc[-1]:
            # print("Crossover: Short Position should Initiate")
            print(Back.RED + "Crossover: 13MA is lower is than 52MA")
            print(Back.RED + "Go SHORT")
            if short_pos == False and long_pos == True:
                pos = close_position(symbol, ticket, volume, entry_price)
                pos = sell_order(symbol)
                print(dt.now(), Back.RED + " Long position Exited and Short Position Initiated")
                short_pos = True
                long_pos = False
            elif short_pos == False and long_pos == False:
                pos = sell_order(symbol)
                short_pos = True
                print(dt.now(), Back.RED + ' No Existing Long Position, Initiated a Short')
            elif long_pos == True:
                pos = close_position(symbol, ticket, volume, entry_price)
                long_pos = False
                print(dt.now(), " Open Long Position Closed as trend changed")
            elif short_pos == True:
                print(dt.now(), Back.RED + " Short: Already with the trend")
                
        time.sleep(sleep) #Keeps refreshing to update data and take actions

#Execution
main(short_filter, long_filter)

#Shutdown
mt5.shutdown()
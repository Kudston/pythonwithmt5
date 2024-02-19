import MetaTrader5 as mt5  # Import the MetaTrader 5 library
import sys  # Import the sys module for system-related functions
import signal  # Import the signal module for signal handling
import time  # Import the time module for time-related functions
import random  # Import the random module for generating random values
import string  # Import the string module for string-related operations
import datetime  # Import the datetime module for working with dates and times

# Connection data
account_id = 78784692  # Example account ID
password = "@h0aDzCa"  # Example password
server = "MetaQuotes-Demo"  # Server name
symbol = "EURUSD"   #symbol traded
lot = 0.1  # Increase the trade volume
deviation = 100  # The variable deviation controls the maximum deviation from the specified price at which an order should be executed.
magic_number = 234000   #unique value used to identify your ea specific positions
symbol_digits = 0   #the symbol digits value(mainly used for conversion of values to pips)
maximum_position_per_trade_open = 200#maximum number of active positions
# Programmer: These are the login details, log in with your MT5 using this account data. Additionally, it would be extremely helpful to open smaller positions like 0.001 or something similar if technically feasible. A spread checker would also be important; otherwise, you might end up with negative trades. Spread = 0...

# Basic trading parameters
symbol_info = None
price_offset = None
stop_loss_ticks = 3  # Stop loss in ticks
take_profit_ticks = 3  # Take profit in ticks
trailing_step = 5  # More aggressive trailing stop step
max_spread_allowed = 5 #specify the max spread allowed
# Programmer: Similarly here, the tick number could be adjustable to 0.0001; one tick is the smallest movement in the market. If technically possible, adjusting to 1/4 of a tick. Adjustable!

ea_start_time = None ##time of launching the ea
local_time_server_time_diff = None
#orders history stores information about history trades
orders_history = {
    "positions_total":0,
    "profits_amount":0,
    "loss_amount":0,
}

# Function to initialize connection to MetaTrader 5
def initialize_mt5():
    try:
        # Initialize the connection to MetaTrader 5
        if not mt5.initialize(login=account_id, password=password, server=server):
            raise Exception(f"Initialize() failed, error code = {mt5.last_error()}")
    except Exception as e:
        log_error(e)
        mt5.shutdown()
        sys.exit()

        # Programmer: I believe everything is okay here, but you can check it.

# Function to check the symbol availability
def check_symbol():
    global symbol_info
    try:
        # Check the availability of the symbol
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise Exception(f"Symbol {symbol} not found.")
    except Exception as e:
        log_error(e)
        mt5.shutdown()
        sys.exit()
        # Programmer: I believe everything is okay here, but you can check it.

# Function to calculate the price offset
def calculate_price_offset():
    global price_offset
    price_offset = 1 * symbol_info.point

    # Programmer: I have some trouble understanding this.
    #conclusion: This is used to set the points above ask and bid price

# Function to generate an order identifier
def generate_order_identifier(ticket_number):
    print(f"Generated order identifier for order: {ticket_number}")

# Programmer: Ticket error, it does not close the opposite...

# Function to place stop orders
def place_stop_orders():
    global local_time_server_time_diff
    try:
        order_identifier = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
        last_tick = mt5.symbol_info_tick(symbol)
        if last_tick is None:
            return
        
        if(abs(last_tick.ask-last_tick.bid)>max_spread_allowed*symbol_info.point):
            msg = "Spread too high. current spread:{}".format(abs(last_tick.ask-last_tick.bid)/symbol_info.point)
            print(msg)
            raise Exception(msg)
        #check if maximum order per time is met
        if mt5.positions_total()>=maximum_position_per_trade_open:
            return

        buy_stop_price = last_tick.ask + price_offset
        sell_stop_price = last_tick.bid - price_offset
        # Place the Buy Stop Order
        buy_order_result = mt5.order_send({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": buy_stop_price,
            "sl": buy_stop_price - stop_loss_ticks * symbol_info.point,
            "tp": buy_stop_price + take_profit_ticks * symbol_info.point,
            "deviation": deviation,
            "magic": magic_number,
            "comment": f"Buy Stop {order_identifier}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })

        # Place the Sell Stop Order
        sell_order_result = mt5.order_send({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "price": sell_stop_price,
            "sl": sell_stop_price + stop_loss_ticks * symbol_info.point,
            "tp": sell_stop_price - take_profit_ticks * symbol_info.point,
            "deviation": deviation,
            "magic": magic_number,
            "comment": f"Sell Stop {order_identifier}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })

        # Check and save ticket numbers
        if buy_order_result.retcode == mt5.TRADE_RETCODE_DONE:
            generate_order_identifier(buy_order_result.order)  # Output the ticket number
            if local_time_server_time_diff is None:
                o_time = mt5.orders_get(ticket=sell_order_result.order)[0].time_setup
                local_time_server_time_diff = o_time - datetime.datetime.now().timestamp()
        else:
            log_error(str(mt5.last_error()))

        if sell_order_result.retcode == mt5.TRADE_RETCODE_DONE:
            generate_order_identifier(sell_order_result.order)  # Output the ticket number
            if local_time_server_time_diff is None:
                o_time = mt5.orders_get(ticket=sell_order_result.order)[0].time_setup
                local_time_server_time_diff = o_time - datetime.datetime.now().timestamp()
        else:
            log_error(str(mt5.last_error()))

    except Exception as e:
        log_error(e)

# Signal handler function for clean script termination
def signal_handler(sig, frame):
    print("Closing all positions and shutting down...")
    closed_all = False
    while not closed_all:
        last_tick = mt5.symbol_info_tick(symbol)
        if last_tick is None:
            raise Exception("Failed to get last tick.")
        closed_all = close_all_positions(last_tick)
        time.sleep(1)
    get_executions_stats()
    mt5.shutdown()
    sys.exit(0)

    # Programmer: When I close the code with Ctrl + C, it should close all orders throughout the code.

# Function to log errors to a file
def log_error(error_message):
    with open("error_log.txt", "a") as file:
        file.write(f"{datetime.datetime.now()}: {error_message}\n")

        # Programmer: Here, it should always indicate if there is an error and what kind of error it is.

# Function to close an order based on its ticket number
def close_order_by_ticket(ticket):
    close_order_result = mt5.order_send({
        "action": mt5.TRADE_ACTION_REMOVE,
        "ticket": ticket
    })
    if close_order_result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Failed to close order {ticket}, error code: {close_order_result.retcode}")

def check_for_close():
    try:
        symbol_orders = [order for order in mt5.orders_get(symbol=symbol)]
        positions = [position for position in mt5.positions_get(symbol=symbol)]

        for order in symbol_orders:
            if order.magic == magic_number:
                req_res = mt5.order_send(
                    {
                    "action":mt5.TRADE_ACTION_REMOVE,
                    "magic":order.magic,
                    "order":order.ticket,
                    }
                )
                if req_res.retcode != mt5.TRADE_RETCODE_DONE:
                    log_error("Error closing order: "+order.ticket+" err: "+mt5.last_error())
                    return False
                print("closed order with ticket number:",order.ticket)

        return True
    except Exception as e:
        log_error(str(e))

def close_all_positions(tick_info):
    try:
        symbol_orders = [order for order in mt5.orders_get(symbol=symbol)]
        positions = [position for position in mt5.positions_get(symbol=symbol)]

        for order in symbol_orders:
            if order.magic == magic_number:
                req_res = mt5.order_send(
                    {
                    "action":mt5.TRADE_ACTION_REMOVE,
                    "magic":order.magic,
                    "order":order.ticket,
                    }
                )
                if req_res.retcode != mt5.TRADE_RETCODE_DONE:
                    log_error("Error closing order: "+order.ticket+" err: "+mt5.last_error())
                    return False
                print("closed order with ticket number:"+order.ticket)
    
        for position in positions:
            if position.magic == magic_number:
                type_close = 1 if position.type==0 else 0
                price_close = tick_info.ask if type_close==0 else tick_info.bid
                req_res = mt5.order_send(
                    {
                    "action":mt5.TRADE_ACTION_DEAL,
                    "position":position.ticket,
                    "symbol":position.symbol,
                    "volume":position.volume,
                    "magic":position.magic,
                    "deviation":deviation,
                    "type":type_close,
                    "price":price_close
                    }
                )
                if req_res.retcode != mt5.TRADE_RETCODE_DONE:
                    log_error("Error closing position: "+order.ticket+" err: "+mt5.last_error())
                    return False
                print("closed a position with ticket number:",position.ticket)
        return True
    except Exception as e:
        log_error(str(e))
        print("Consider Close the positions manually as we have encountered an error while closing positions.")
        return True
    
def get_executions_stats():
    try:
        global  orders_history
        history_positions = mt5.history_deals_get(ea_start_time+local_time_server_time_diff,
                                datetime.datetime.now().timestamp()+local_time_server_time_diff,
                                group="{}".format(symbol))
        closed_positions = []
        for deal in history_positions:
            if deal.entry in [1,3]:
                closed_positions.append(deal)
        total_positions = len(closed_positions)
        profits_earned = 0
        loss_earned = 0
        for each in closed_positions:
            if each.profit >0:
                profits_earned+=each.profit
            elif each.profit<0:
                loss_earned+=each.profit
        orders_history["positions_total"] = total_positions
        orders_history["profits_amount"] = profits_earned
        orders_history["loss_amount"] = loss_earned
        print("Server Trade start time:",datetime.datetime.fromtimestamp(ea_start_time+local_time_server_time_diff))
        seconds_elapsed = int((datetime.datetime.now().timestamp()+local_time_server_time_diff)-
                  (ea_start_time+local_time_server_time_diff))
        print("Minutes: ", int(seconds_elapsed/60)," Seconds: ",(seconds_elapsed%60))
        print(orders_history)
    except Exception as e:
        log_error(str(e))

# Main function
def main():
    initialize_mt5()
    check_symbol()
    calculate_price_offset()
    global ea_start_time
    ea_start_time = datetime.datetime.now().timestamp()

    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        last_tick_value = 0 #To keep track of every tick time
        while True:
            #==============#######===============#
            ## This block checks for new tick
            last_tick = mt5.symbol_info_tick(symbol)
            if last_tick is None:
                raise Exception("Failed to get last tick.")
            
            #==============#######===============#
            #check if there are opened orders, closes them, if there is an open we don't place new positions
            if last_tick_value!=last_tick.time_msc:
                if not check_for_close():
                    continue

            last_tick_value = last_tick.time_msc
            place_stop_orders()
            # close_opposite_positions(symbol)  # Close opposite positions
            time.sleep(1)  # Sleep time could be adjusted as needed, 0 is the best option for HFT, better use a higher number when testing the script
    except KeyboardInterrupt:
        print("Script execution stopped by user.")

if __name__ == "__main__":
    main()

# Programmer: This is the end; I might have forgotten to mention something, so there might be some small additions later on. Don't be surprised afterward.

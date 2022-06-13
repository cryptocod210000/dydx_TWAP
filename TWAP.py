#Websocket
#!/usr/bin/env python
import websocket, json
import time
import os
import sys
from sortedcontainers import SortedDict
from decimal import Decimal
from dydx3 import Client
from web3 import Web3
import pandas as pd

from dydx3.constants import *
from dydx3.constants import POSITION_STATUS_OPEN
from decimal import Decimal
import datetime

ETHEREUM_ADDRESS = '#INSERT YOU ETHEREUM ADDRESS HERE'
private_client = Client(
    host='https://api.dydx.exchange',
    api_key_credentials={ 'key': '#INSERT YOUR API KEY HERE', 
                         'secret': '#INSERT YOUR API SECRET HERE', 
                         'passphrase': '#INSERT YOUR API PASSPHRASE HERE'},
    stark_private_key='#INSERT YOUR STARK PRIVATE KEY HERE',
    default_ethereum_address=ETHEREUM_ADDRESS,
)

account_response = private_client.private.get_account()
position_id = account_response.data['account']['positionId']

direction =  sys.argv[1]
security_name = sys.argv[2] 
total_size = float(sys.argv[3])
duration = float(sys.argv[4]) #in minutes
time_increment = str(sys.argv[5])


if direction == "buy" or direction=='Buy':
    SIDE = str(ORDER_SIDE_BUY)
    price = "1000000000"
elif direction == "sell" or direction=='Sell':
    SIDE = str(ORDER_SIDE_SELL)
    price = "0.001"
else:
    print("Error in direction entered")

rate = total_size/duration

api_file = open("./dydx_api_file.json", "r")
output = api_file.read()
res = json.loads(output)
rounding_decimal = res[str(security_name)]["rounding"]

# Initiate empty arrays to track volume & price
volume_array = []
price_array = []

count = 1
show_order=1

start_time = datetime.datetime.now()

if time_increment == "seconds":
	next_execution = start_time + datetime.timedelta(seconds=10)
	end_time = start_time + datetime.timedelta(minutes=duration+0.1)
	rate = total_size/(duration*60)*10
elif time_increment == "minutes":
	next_execution = start_time + datetime.timedelta(minutes=1)
	end_time = start_time + datetime.timedelta(minutes=duration+0.1)
	rate = total_size/duration
elif time_increment == "hours":
	next_execution = start_time + datetime.timedelta(hours=1)
	end_time = start_time + datetime.timedelta(minutes=duration+0.1)
	rate = total_size/(duration/60) 

no_orders = total_size/rate
order_counter=0
    
def run_script():
	def on_open(ws):
	    print("opened")
	    channel_data = { "type": "subscribe", "channel": "v3_orderbook", "id": str(security_name), "includeOffsets": "True"}
	    ws.send(json.dumps(channel_data))

	def on_message(ws, message):
		global position_id, rate, count, start_time, next_execution, time_increment, end_time, rate, show_order, no_orders, order_counter
		now = datetime.datetime.now()

		if ((next_execution > now) and (end_time > next_execution) and (end_time > now) and (show_order==1)):
			print("Next order: ", str(next_execution.strftime("%H:%M:%S - %D")))
			show_order=0
			count +=1

		elif ((next_execution < now) and (end_time > next_execution)):
			try:
				order_params = {'position_id': position_id, 'market': security_name, 'side': SIDE,
				                'order_type': ORDER_TYPE_MARKET, 'post_only': False, 'size': str(rate), 'price': price, 
				                'limit_fee': '0.0015', 'expiration_epoch_seconds': time.time() + 120, "time_in_force": TIME_IN_FORCE_FOK}
				order_dict = private_client.private.create_order(**order_params)
				order_id = order_dict.data['order']['id']
				order_counter+=1
				print("order submitted #", order_counter, " of ", no_orders, " - End time:", str(end_time.strftime("%H:%M:%S - %D")))
				show_order=1
			except Exception as e:
				try:
					print(e.msg['errors'][0]['msg'])
					ws.close()
				except:
					print(e)
					ws.close()

			orders_filled = pd.DataFrame(private_client.private.get_fills(market=security_name, limit=int(order_counter)).data['fills'])
			orders_filled['price'] = pd.to_numeric(orders_filled['price'])
			print("Filled", direction, rate, security_name, "@", orders_filled.iloc[0]['price'], " --- ",
				int(order_counter), "/", int(no_orders), "orders filled @ avg", round(orders_filled["price"].mean(),5))
            
			print("-----------------------------------------------------------------------------")


			if time_increment == "seconds":
				next_execution = next_execution + datetime.timedelta(seconds=10)
			elif time_increment == "minutes":
				next_execution = next_execution + datetime.timedelta(minutes=1)
			elif time_increment == "hours":
				next_execution = next_execution + datetime.timedelta(hours=1)
			count +=1
            
		elif (end_time < now):
			orders_filled = pd.DataFrame(private_client.private.get_fills(market=security_name, limit=int(no_orders)).data['fills'])
			orders_filled['price'] = pd.to_numeric(orders_filled['price'])
			print("Average orders filled @ ", orders_filled["price"].mean())
			ws.close()
            
	def on_close(ws):
	    print("### closed ###")
	    
	socket = "wss://api.dydx.exchange/v3/ws"
	ws = websocket.WebSocketApp(socket, on_open=on_open, on_message=on_message, on_close=on_close)
	ws.run_forever()

if __name__ == "__main__":
    try:
        run_script()
    except Exception as err:
        print(err)
        print("connect failed")

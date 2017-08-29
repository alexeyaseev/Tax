#1. pay attention to adding orders from previous year to input file
#2. pay attention that currency file should contain data from previous year if trade was open previous year
#3. edit output file so that sell and buy quantities for every ticker are zero (if subtotal is present
#   then there is no need for edit)
#4. specify input and output files and mode
#    (SIMPLE mode: outputs trades with curexch info, NOT SIMPLE MODE: fullfills orders on FIFO rule)
INPUT_FILE  = './2016_IB.csv'
OUTPUT_FILE_TRADES = './2016_rub_trades.csv'
OUTPUT_FILE_FEES   = './2016_rub_fees.csv'
OUTPUT_FILE_DIVIDENDS = './2016_rub_dividends.csv'
EXCH_FILE   = './usd_rub.txt'
SIMPLE_MODE = False

import csv
import datetime
import pandas as pd

#1. read source report into 'lines'
with open( INPUT_FILE, newline='') as csvfile:
    data = csv.reader(csvfile, delimiter=',', quotechar='"')
    lines = [line for line in data]

#2. read currency exchange file
curexch = {}
with open( EXCH_FILE ) as fileId:
    for line in fileId:
        (date, price) = line.split('\t')
        date = datetime.datetime.strptime( date, '%Y-%m-%d' ).date()
        curexch[ date ] = float(price.strip())

#3. trades report
output = {}

#Trades,Data,Order,Stocks,USD,AAPL,"2016-03-29, 10:08:48",100,106.08,107.68,-10608,-1,10609,0,160,O
TICKER, DATETIME, Q, PRICE, CPRICE, TOTAL, COMM, BASIS, PL, MTM, TRADETYPE = range(5, 16);

orders = []
for vals in lines:
    if vals[0] != "Trades": continue
    if vals[1] == "Header": continue #TODO?: parse column names
    if vals[1] == "Total": continue
    if vals[1] == "SubTotal":
        orders.clear()
        continue
    
    ticker = vals[ TICKER ]
    if ticker not in output: output[ ticker ] = { }
    tradetype = vals[ TRADETYPE ]
    q = int( vals[ Q ].replace(',',''))
    date, time = vals[ DATETIME ].split(',')
    date = datetime.datetime.strptime( date, '%Y-%m-%d' ).date()
    price_usd = float( vals[ PRICE ] )
    comm_usd  = float( vals[ COMM ] )

    if SIMPLE_MODE:
        key = len(output[ticker])
        output[ticker][key] = [date, q, price_usd, comm_usd]
        continue
    
    if tradetype not in ["O","C","O;P","C;P"]:
        print( "Trade type is unknown: ", tradetype )
        break

    if tradetype in ["O","O;P"]:
        orders.append( (date, time, q, price_usd, comm_usd) )
    else: #close order
        key = str(date) + time + str(price_usd)
        if key not in output[ ticker ]: output[ticker][key] = [date, 0, price_usd, 0]
        output[ticker][key][3] += comm_usd
        comm_usd = 0
            
        while q: #fill until q > 0
            prev_date, prev_time, prev_q, prev_price_usd, prev_comm_usd = orders.pop(0)

            qq = min(abs(q),abs(prev_q)) * prev_q / abs(prev_q)

            #open order
            key = str(prev_date) + prev_time + str(prev_price_usd)
            if key not in output[ ticker ]: output[ ticker ][ key ] = [prev_date, 0, prev_price_usd, 0]
            output[ticker][key][1] += qq
            output[ticker][key][3] += prev_comm_usd

            #close order
            key = str(date) + time + str(price_usd)
            output[ticker][key][1] -= qq

            prev_q, q = prev_q - qq, q + qq

            if prev_q != 0:
                orders.insert(0, (prev_date, prev_time, prev_q, prev_price_usd, 0) )

df = pd.DataFrame(columns=('Название акции', 'Дата', 'Кол-во', 'Цена акции(доллар)', 'Продажа(доллар)',
                           'Покупка(доллар)', 'Комиссия(доллар)', 'Курс доллара', 'Продажа(руб)',
                           'Покупка(руб)', 'Комиссия(руб)'))
total_comm_usd = total_comm_adj = 0
total_sell_usd = total_buy_usd = 0
total_sell_adj = total_buy_adj = 0
subtotal_comm_usd = subtotal_comm_adj = 0
subtotal_sell_usd = subtotal_buy_usd = 0
subtotal_sell_adj = subtotal_buy_adj = 0
for ticker in sorted(output):
    for date_time in sorted(output[ticker]):
        date, q, price_usd, comm_usd = output[ticker][date_time]
        exch_rate = curexch[ date ]
        sell_usd = (-q if q < 0 else 0) * price_usd
        sell_adj = sell_usd * exch_rate
        buy_usd  = (-q if q > 0 else 0) * price_usd
        buy_adj  = buy_usd  * exch_rate
        comm_adj = comm_usd * exch_rate
        subtotal_comm_usd += comm_usd
        subtotal_comm_adj += comm_adj
        subtotal_sell_usd += sell_usd
        subtotal_sell_adj += sell_adj
        subtotal_buy_usd  += buy_usd
        subtotal_buy_adj  += buy_adj
        df.loc[len(df)-1] = (ticker, date, q, price_usd, sell_usd, buy_usd, comm_usd, exch_rate, sell_adj, buy_adj, comm_adj)
    total_comm_usd += subtotal_comm_usd
    total_comm_adj += subtotal_comm_adj
    total_sell_usd += subtotal_sell_usd
    total_buy_usd  += subtotal_buy_usd
    total_sell_adj += subtotal_sell_adj
    total_buy_adj  += subtotal_buy_adj
    subtotal_profit_usd = subtotal_sell_usd + subtotal_buy_usd + subtotal_comm_usd
    subtotal_profit_adj = subtotal_sell_adj + subtotal_buy_adj + subtotal_comm_adj
    df.loc[len(df)-1] = ('','','','Итого:', subtotal_sell_usd, subtotal_buy_usd, subtotal_comm_usd, '',
                         subtotal_sell_adj, subtotal_buy_adj, subtotal_comm_adj)
    df.loc[len(df)-1] = ('','','','Прибыль(доллар):', subtotal_profit_usd, '', '', 'Прибыль(руб):', subtotal_profit_adj, '', '')
    df.loc[len(df)-1] = ('',) * len(df.columns)
    subtotal_sell_usd = subtotal_buy_usd = subtotal_comm_usd = 0
    subtotal_sell_adj = subtotal_buy_adj = subtotal_comm_adj = 0

total_profit_usd = total_sell_usd + total_buy_usd + total_comm_usd
total_profit_adj = total_sell_adj + total_buy_adj + total_comm_adj
df.loc[len(df)-1] = ('','','','Итого:', total_sell_usd, total_buy_usd, total_comm_usd, '',total_sell_adj, total_buy_adj, total_comm_adj)
df.loc[len(df)-1] = ('','','','Прибыль(доллар):', total_profit_usd, '', '', 'Прибыль(руб):',total_profit_adj, '', '')

#print('\n', df)
df.to_csv( OUTPUT_FILE_TRADES, index=False, encoding='utf8' )

#4. fees and interest report
df = pd.DataFrame(columns=('Дата', 'Название расхода', 'Сумма (доллар)', 'Курс доллара', 'Сумма (руб)'))
total_usd = total_adj = 0
for vals in lines:
    if vals[0] not in [ "Interest", "Fees" ]: continue
    if vals[1] != "Data": continue
    if vals[2] == "Total": continue

    index = 3 if vals[0] == "Interest" else 4
    date = datetime.datetime.strptime( vals[ index + 0 ], '%m/%d/%Y').date()
    desc = vals[ index + 1 ]
    amount_usd = float(vals[ index + 2 ])
    amount_adj = amount_usd * curexch[ date ]
    total_adj += amount_adj
    total_usd += amount_usd

    df.loc[len(df)-1] = (date, desc, amount_usd, curexch[ date ], amount_adj)
df.loc[len(df)-1] = ('','Итого(доллар):', total_usd, 'Итого(руб):', total_adj) 

#print('\n',df)
df.to_csv( OUTPUT_FILE_FEES, index=False, encoding='utf8' )

#5. dividend report
df = pd.DataFrame(columns=('Дата', 'Название дивиденда', 'Сумма (доллар)', 'Курс доллара', 'Сумма (руб)'))
total_usd = total_adj = 0
for vals in lines:
    if vals[0] not in [ "Dividends" ]: continue
    if vals[1] != "Data": continue
    if vals[2] == "Total": continue
    
    date = datetime.datetime.strptime( vals[ 3 ], '%m/%d/%Y').date()
    desc = vals[ 4 ]
    amount_usd = float(vals[ 5 ])
    amount_adj = amount_usd * curexch[ date ]
    total_adj += amount_adj
    total_usd += amount_usd

    df.loc[len(df)-1] = (date, desc, amount_usd, curexch[ date ], amount_adj)
df.loc[len(df)-1] = ('','Итого(доллар):', total_usd, 'Итого(руб):', total_adj)

#print('\n',df)
df.to_csv( OUTPUT_FILE_DIVIDENDS, index=False, encoding='utf8' )

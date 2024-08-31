#1. pay attention that currency file should contain data from previous year if trade was open previous year
#2. specify input and output files

YEAR = '2021'
INPUT_FILE  = f'./{YEAR}_IB.csv'
OUTPUT_FILE_TRADES = f'./{YEAR}_rub_trades.csv'
OUTPUT_FILE_FEES   = f'./{YEAR}_rub_fees.csv'
OUTPUT_FILE_DIVIDENDS = f'./{YEAR}_rub_dividends.csv'
EXCH_FILE   = './usd_rub.txt'

import csv
import datetime
import pandas as pd
import collections

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

#0.Trades, 1.Header, 2.DataDiscriminator, 3.Asset Category, 4.Currency, 5.Symbol, 6.Date/Time, 7.Exchange,
#8.Quantity, 9.T. Price, 10.C. Price, 11.Proceeds, 12.Comm/Fee, 13.Basis, 14.Realized P/L, 15.MTM P/L, 16.Code
#Trades,Data,Order,Stocks,USD,AMD,"2017-02-01, 09:43:33",-,300,11.318333333,12.06,-3395.5,-1.4,3396.9,0,222.5,O;P

TICKER, DATETIME, Q, PRICE, COMM, TRADETYPE = 5, 6, 8, 9, 12, 16
open_orders = []
close_orders = []
for vals in lines:
    if vals[0] != "Trades": continue    
    if vals[1] == "Header": continue #TODO?: parse column names
    if vals[1] == "Total": continue
    if vals[3] not in ["Stocks", "Equity and Index Options"]: continue
    if vals[1] == "SubTotal": #process open and close orders for ticker
        print(ticker)
        output[ ticker ] = collections.OrderedDict()
        for date, q, price_usd, comm_usd, tradetype in close_orders:
            while q: #fill until q > 0
                prev_date, prev_q, prev_price_usd, prev_comm_usd = open_orders[0]               
                
                if prev_q * q > 0: #"C;O" trade
                    if tradetype not in ["C;O;P", "C;O"]:
                        print("algorithm is broken: tradetype != C;O;P or C;O, but quantity is not filled")
                        break
                    else:
                        break
                open_orders.pop(0)
                
                #open order
                key = str(prev_date) + str(prev_price_usd)
                if key not in output[ ticker ]: output[ ticker ][ key ] = [prev_date, 0, prev_price_usd, 0]
                output[ticker][key][1] += prev_q
                output[ticker][key][3] += prev_comm_usd

                #close order
                key = str(date) + str(price_usd)
                if key not in output[ ticker ]: output[ticker][key] = [date, 0, price_usd, 0]
                output[ticker][key][1] -= prev_q
                output[ticker][key][3] += comm_usd

                comm_usd = 0

                q += prev_q
                            
                ## if 'ClosedLot' is not used:
                #qq = min(abs(q),abs(prev_q)) * prev_q / abs(prev_q)
                #prev_q, q = prev_q - qq, q + qq
                #if prev_q != 0:
                #    open_orders.insert(0, (prev_date, prev_q, prev_price_usd, 0) )

        open_orders.clear()
        close_orders.clear()
        continue

    ticker = vals[ TICKER ]
    tradetype = vals[ TRADETYPE ]
    q = float(vals[ Q ].replace(',',''))
    if vals[3] == "Equity and Index Options":
        q *= 100
    date = vals[ DATETIME ].split(',')[0]
    date = datetime.datetime.strptime( date, '%Y-%m-%d' ).date()
    price_usd = float( vals[ PRICE ] )
    comm_usd  = float( vals[ COMM ] ) if vals[ COMM ] else 0
    
    #if vals[2] == "Order" and tradetype in ["O","O;P"]:
    if vals[2] == "ClosedLot":
        open_orders.append( (date, q, price_usd, comm_usd) )
    elif vals[2] == "Order" and tradetype in ["C","C;P","C;L;P","C;O;P","C;L","C;O","A;C","C;Ep"]:
        close_orders.append( (date, q, price_usd, comm_usd, tradetype) )

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
    for key in output[ticker]:
        date, q, price_usd, comm_usd = output[ticker][key]
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
    if "Total" in vals[2]: continue

    currency = vals[2]
    index = 3 if vals[0] == "Interest" else 4
    date = datetime.datetime.strptime( vals[ index + 0 ], '%Y-%m-%d').date()
    desc = vals[ index + 1 ]
    amount_usd = float(vals[ index + 2 ])
    amount_adj = amount_usd * curexch[ date ]        

    if currency == "RUB":
        amount_usd = 0
        amount_adj = amount_usd

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
    
    date = datetime.datetime.strptime( vals[ 3 ], '%Y-%m-%d').date()
    desc = vals[ 4 ]
    amount_usd = float(vals[ 5 ])
    amount_adj = amount_usd * curexch[ date ]
    total_adj += amount_adj
    total_usd += amount_usd

    df.loc[len(df)-1] = (date, desc, amount_usd, curexch[ date ], amount_adj)
df.loc[len(df)-1] = ('','Итого(доллар):', total_usd, 'Итого(руб):', total_adj)

#print('\n',df)
df.to_csv( OUTPUT_FILE_DIVIDENDS, index=False, encoding='utf8' )

# FIRST and LAST day of year should be manualy put in input file if absent

import datetime

# reading input
data = {}
firstDate = lastDate = ''
with open('./usd_rub_CBR.txt') as fileId:
    for line in fileId.readlines():
        date, price = line.split('\t')
        date = datetime.datetime.strptime(date, '%m/%d/%Y').date()
        price = price.strip()
        if not data: firstDate = date
        data[ date ] = price.strip()        
        lastDate = date

# writing output
lastPrice = data[ firstDate ]
with open('./usd_rub.txt', 'w') as fileId:
    for days in range((lastDate - firstDate).days + 1):
        date = firstDate + datetime.timedelta(days = days)
        if date in data: lastPrice = data[ date ]
        fileId.write(date.strftime('%Y-%m-%d'))
        fileId.write('\t')
        fileId.write(lastPrice)
        fileId.write('\n')

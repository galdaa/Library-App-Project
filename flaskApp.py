from flask import Flask, render_template, request, redirect, url_for #flask env
from datetime import datetime # for history
from cachetools import TTLCache # add caching for speed

#to use google sheet API:
import gspread 
from oauth2client.service_account import ServiceAccountCredentials # google API

#book_allowed_types = {"SA", "AA", "S~ANON", "L-ANON"}
STOCK_QUAN_COL_FILE_INDEX =  3
MONEY = "Money"
HISTORY = "History"
ORDER = "Order"

#access to google api defines
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#connect json key file
CREDS = ServiceAccountCredentials.from_json_keyfile_name("library-app-project-482610-8a2b41102d15.json", SCOPE)
CLIENT = gspread.authorize(CREDS)
SPREADSHEET = CLIENT.open("Lib App Info")


#TODO - add future orders from file display and update

#cache for 10min
cache = TTLCache(maxsize=100, ttl=600) 

app = Flask(__name__)

#method to connect google
def get_sheet(name):
    return SPREADSHEET.worksheet(name)

#load sheet file to cache
def load_data():	
	if 'items_data' in cache:
		print("Loading data from Cache")
		return cache['items_data']
	
	book_types = ["SA", "AA", "S-ANON", "L-ANON"]
	items = []
	for book_type in book_types:
		type_data = {
        	'book_type' : book_type,
        	'books' : get_sheet(book_type).get_all_records()
        }
		items.append(type_data)
	print(f"data was loaded:{items}")
	cache['items_data'] = items # save in cache
	print(f"Data was loaded from Google and cached.")
	return items

#home page for navigation
@app.route('/')
def home():
	return render_template('home.html')

#page for stock view   
@app.route('/stock_view')
def stock_view():
	items = load_data()
	return render_template('stock_page.html', items = items)

#############################################
# sell page:								#
# get from sell.html sell details : 		#
# list of books- types, names, quantities 	#
#############################################
@app.route('/sell', methods=['GET', 'POST'])
def sell_page():
	items = load_data()
	book_types = []
	book_names = []
	book_prices = []
	quantities = []
	if request.method == 'POST':
		print("\n~~s~~\n")
		book_types = request.form.getlist('book_types[]')
		book_names = request.form.getlist('book_names[]')
		book_prices = request.form.getlist('book_prices[]')
		quantities = request.form.getlist('quantities[]')
		print(book_types,book_names,book_prices,quantities)
		print("\n~e~\n")
	return render_template('sell.html', items = items)

#################################################################
# sell execution page:						                    #
# get from place_order.html sell details + seller name and	:   #
# do total price calc.  										#
# update sheet file in: relevant stock, money it get, history 	#
#################################################################
@app.route('/place_order', methods=['POST'])
def place_order():
	book_types = request.form.getlist('book_types[]')
	book_names = request.form.getlist('book_names[]')
	book_prices = request.form.getlist('book_prices[]')
	quantities = request.form.getlist('quantities[]')
	Clean_order(book_types, book_names, book_prices, quantities)
	total_prices = []
	total_prices = Calc_total_prices(book_prices, quantities)
	print(f"total Order: \nTyeps: {book_types} \nNames: {book_names} \n"
		f"Prices: {book_prices} \nQuantities: {quantities} \ntotals: {total_prices}")
	total = Calc_total(total_prices)
	if request.form.get('confirm_action') == 'true':
		Sell_order_update(book_types, book_names, quantities)
		Add_money(total)
		cache.clear()
		print("Cache cleared after sale to ensure fresh data.")
		seller = request.form.get('seller')
		print(seller)
		Add_history(seller, book_types, book_names, quantities, total_prices)
		return redirect(url_for('home'))
	return render_template('place_order.html', book_types = book_types, 
						book_names = book_names, book_prices = book_prices, 
						quantities = quantities, total_prices = total_prices, total = total)

def Sell_order_update(book_types, book_names, quantities):
	for i in range(len(book_names)):
		sheet = get_sheet(book_types[i])
		cell = sheet.find(book_names[i])
		quan = int(quantities[i])
		row_index = cell.row
		curr_stock = int(sheet.cell(row_index, STOCK_QUAN_COL_FILE_INDEX).value)
		new_stock = int(curr_stock - quan)
		sheet.update_cell(row_index, STOCK_QUAN_COL_FILE_INDEX, new_stock)
		print(f"Updated {book_names[i]}: {curr_stock} -> {new_stock}")

def Add_money(money):
	sheet = get_sheet(MONEY)
	curr_money = int(sheet.cell(1, 1).value)
	new_money = int(curr_money + int(money))
	sheet.update_cell(1, 1, new_money)
	print(f"Updated Money {curr_money} + {money} = {new_money}")

def Get_money():
	sheet = get_sheet(MONEY)
	return int(sheet.cell(1, 1).value)

def Add_history(seller, book_types, book_names, quantities, prices):
	now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
	sheet = get_sheet(HISTORY)
	for i in range(len(book_types)):
		row = [now, seller, book_types[i], book_names[i], quantities[i], prices[i]]
		if (i == (len(book_types) - 1)):
			row.append(Get_money())
		sheet.append_row(row)

def Calc_total(total_prices):
	total = 0
	for price in total_prices:
		total += int(price)
	return total

def Calc_total_prices(book_prices, quantities):
	total_prices = []
	i = 0
	while i < len(quantities):
		total_prices.append(int( int(quantities[i]) *int(book_prices[i]) ))
		print(f"total : {int(quantities[i])}*{int(book_prices[i])}="
			f"{ int(quantities[i]) * int(book_prices[i]) }={total_prices[i]}")
		i += 1
	return total_prices

def Clean_order(book_types, book_names, book_prices, quantities):
	i = 0
	while i < len(quantities):
		if int(quantities[i]) == 0:
			del book_types[i]
			del book_names[i]
			del book_prices[i]
			del quantities[i]
			i -= 1
		i += 1

@app.route('/order_page', methods=['GET', 'POST'])
def order_page():
	items = load_data()
	book_types = []
	book_names = []
	book_prices = []
	quantities = []
	if request.method == 'POST':
		print("\n~~s~~\n")
		book_types = request.form.getlist('book_types[]')
		book_names = request.form.getlist('book_names[]')
		book_prices = request.form.getlist('book_prices[]')
		quantities = request.form.getlist('quantities[]')
		print(book_types,book_names,book_prices,quantities)
		print("\n~e~\n")
	return render_template('order2stock.html', items = items)

@app.route('/place_order2stock', methods=['POST'])
def place_order2stock():
	book_types = request.form.getlist('book_types[]')
	book_names = request.form.getlist('book_names[]')
	book_prices = request.form.getlist('book_prices[]')
	quantities = request.form.getlist('quantities[]')
	Clean_order(book_types, book_names, book_prices, quantities)
	total_prices = []
	total_prices = Calc_total_prices(book_prices, quantities)
	print(f"total Order: \nTyeps: {book_types} \nNames: {book_names} \n"
		f"Prices: {book_prices} \nQuantities: {quantities} \ntotals: {total_prices}")
	total = Calc_total(total_prices)
	if request.form.get('confirm_action') == 'true':
		#Sell_order_update(book_types, book_names, quantities)
		#Add_money(total)
		cache.clear()
		print("Cache cleared after order to ensure fresh data.")
		#Add_history(book_types, book_names, quantities, total_prices)
		return redirect(url_for('home'))
	return render_template('place_order2stock.html', book_types = book_types, 
						book_names = book_names, book_prices = book_prices, 
						quantities = quantities, total_prices = total_prices, total = total)

if __name__ == '__main__':
    app.run(debug=True)
  
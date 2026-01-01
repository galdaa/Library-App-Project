from flask import Flask, render_template, request, redirect, url_for #flask env

#to use google sheet API:
import gspread 
from oauth2client.service_account import ServiceAccountCredentials # google API

#book_allowed_types = {"SA", "AA", "S~ANON", "L-ANON"}
STOCK_QUAN_COL_FILE_INDEX =  3
#access to google
#TODO - add future orders from file display and update
app = Flask(__name__)

#method to connect google
def get_sheet(name):
    #access to google
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    #connect json key file
    creds = ServiceAccountCredentials.from_json_keyfile_name("library-app-project-482610-8a2b41102d15.json", scope)
    client = gspread.authorize(creds)
    print("Logged in successfully as:", creds.service_account_email)
    return client.open("Lib App Info").worksheet(name)# sheet file name #.worksheet("AA")
    #return client.open_by_key("Lib App Info")

def load_data():	
	book_types = {"SA", "AA", "S-ANON", "L-ANON"}
	items = []
	for book_type in book_types:
		type_data = {
        	'book_type' : book_type,
        	'books' : get_sheet(book_type).get_all_records()
        }
		items.append(type_data)
	print(f"data was loaded:{items}")
	return items

@app.route('/')
def home():
	#items = load_data()
	return render_template('home.html')
    
@app.route('/stock_view')
def stock_view():
	items = load_data()
	return render_template('stock_page.html', items = items)

@app.route('/order', methods=['GET', 'POST'])
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
	return render_template('order.html', items = items)

@app.route('/place_order', methods=['POST'])
def place_order():
	book_types = request.form.getlist('book_types[]')
	book_names = request.form.getlist('book_names[]')
	book_prices = request.form.getlist('book_prices[]')
	quantities = request.form.getlist('quantities[]')
	#print(f"Received Order: \nTyeps: {book_types} \nNames: {book_names} \nQuantities: {quantities}")
	Clean_order(book_types, book_names, book_prices, quantities)
	print(f"clean Order: \nTyeps: {book_types} \nNames: {book_names} \n"
		f"Prices: {book_prices} \nQuantities: {quantities}")
	total_prices = []
	total_prices = Calc_total_prices(book_prices, quantities)
	print(f"total Order: \nTyeps: {book_types} \nNames: {book_names} \n"
		f"Prices: {book_prices} \nQuantities: {quantities} \ntotals: {total_prices}")
	total = Calc_total(total_prices)
	if request.form.get('confirm_action') == 'true':
		Sell_order_update(book_types, book_names, quantities)
		return redirect(url_for('home'))
	return render_template('place_order.html', book_types = book_types, 
						book_names = book_names, book_prices = book_prices, 
						quantities = quantities, total_prices = total_prices, total = total)
	#return redirect(url_for('stock_view'))

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

if __name__ == '__main__':
    app.run(debug=True)
  
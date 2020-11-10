from __future__ import print_function
from flask import Flask, render_template, session, json, request, redirect, flash
from flask_mysqldb import MySQL
from google.oauth2 import service_account
from googleapiclient.discovery import build
import boxsdk
import json
import re
from datetime import datetime
import os
import glob

app = Flask(__name__)
app.config["SECRET_KEY"] = "ShuJAxtrE8tO5ZT"

# MySQL configurations
with open('mysql.cfg', 'r') as mysql_cfg:
	mysql_cfg_lines = mysql_cfg.read().splitlines()
	app.config['MYSQL_USER'] = mysql_cfg_lines[0]
	app.config['MYSQL_PASSWORD'] = mysql_cfg_lines[1]
	app.config['MYSQL_DB'] = mysql_cfg_lines[2]
	app.config['MYSQL_HOST'] = mysql_cfg_lines[3]
mysql = MySQL(app)

#Google Translate and Sheets credentials
tr_credentials = service_account.Credentials.from_service_account_file("My Project-1f2512d178cb.json")
translate_client = translate.Client(credentials=tr_credentials)

scopes = ['https://www.googleapis.com/auth/spreadsheets']
scoped_gs = tr_credentials.with_scopes(scopes)
sheets_client = build('sheets', 'v4', credentials=scoped_gs)
sheet = sheets_client.spreadsheets()
tracking_ws = "1F4nXX1QoyV1miaRUop2ctm8snDyov6GNu9aLt9t3a3M"
ranges = "Workflow_Tracking!A3:L87075"
gsheet = sheet.values().get(spreadsheetId=tracking_ws, range=ranges, majorDimension="COLUMNS").execute()

#Box API configurations
with open('box_config.json', 'r') as f:
	boxapi = json.load(f)
box_auth = boxsdk.JWTAuth(
	client_id=boxapi["boxAppSettings"]["clientID"],
    client_secret=boxapi["boxAppSettings"]["clientSecret"],
    enterprise_id=boxapi["enterpriseID"],
    jwt_key_id=boxapi["boxAppSettings"]["appAuth"]["publicKeyID"],
    rsa_private_key_data=boxapi["boxAppSettings"]["appAuth"]["privateKey"],
    rsa_private_key_passphrase=boxapi["boxAppSettings"]["appAuth"]["passphrase"],
)

box_access_token = box_auth.authenticate_instance()
box_client = boxsdk.Client(box_auth)

# Google Translate utility
def dataTranslate(data):
	indices = []
	for d in data:
		indices.append(d[0])

	transdata = []
	dataplustrans = []
	for d in data:
		translation = translate_client.translate(d[1], target_language="en", source_language="it")
		transdata.append(translation['translatedText'])
		dlist = list(d)
		dlist.append(translation['translatedText'])
		dataplustrans.append(dlist)
	return dataplustrans, indices

#Roman numeral utility
def toRoman(data):
	romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
	romin = int(data) - 1
	if romin >= 0 and romin < len(romans):
		romreg = romans[romin]
	else:
		romreg = data
	return romreg

@app.route("/") # Home page
def index():
	return render_template('index.html')

@app.route("/login", methods=['POST']) # Login form
def login():
	error = ""
	with open('user.cfg', 'r') as user_cfg:
		user_lines = user_cfg.read().splitlines()
		username = user_lines[0]
		password = user_lines[1]
	if request.form['password'] == password and request.form['username'] == username:
		session['logged_in'] = True
	else:
		error = 'Sorry, wrong password!'
	return render_template('index.html', error=error)

@app.route('/init', methods=['POST']) #Form submitted from home page
def init():
	if (request.form.get('region')):
		session['region'] = request.form['region']
	else:
		session['region'] = ""
	if (request.form.get('insula')):
		session['insula'] = request.form['insula']
	else:
		session['insula'] = ""
	if (request.form.get('property')):
		session['property'] = request.form['property']
	else:
		session['property'] = ""
	if (request.form.get('room')):
		session['room'] = request.form['room']
	else:
		session['room'] = ""

	prop = session['property']
	if session['property'].isalpha():
		prop += "1"
	elif len(session['property']) < 2:
		prop = "0" + prop
	ins = session['insula']
	if len(session['insula']) < 2:
		ins = "0" + ins
	building = toRoman(session['region']) + ins + prop + session['room']
	values = gsheet.get('values', [])
	locationlist = values[0]
	arclist = values[6]
	links = values[10]

	session['ARClist'] = {}

	for l in range(len(locationlist)):
		if locationlist[l].startswith(building):
			session['ARClist'][arclist[l]] = {"link": "None", 
											  "is_art": "Not defined",
											  "is_plaster": "Not defined",
											  "notes": "",
											  "done": False,
											  "current": False,
											  "trackerindex": l}
			if links[l]:
				session['ARClist'][arclist[l]]["link"] = links[l]

	for a,v in session['ARClist'].items():
		pass
		#db query: get things where ARC == a or other_arcs contains a

	return redirect('/ARCs')

@app.route('/ARCs')
def chooseARCs():
	return render_template("chooseARCs.html", arcs = session['ARClist'], 
		                   region=session['region'], insula=session['insula'], 
		                   property=session['property'], room=session['room'])

@app.route('/makedoc/<chosenarc>')
def makedoc(chosenarc):
	session['ARClist'][chosenarc]['current'] = True
	arcdeets = session['ARClist'][chosenarc]
	if arcdeets['link'].contains('http'):
		#use this link, we're good
		pass
	else:
		#make new doc 
		pass
	return redirect('/PPP')

@app.route("/PPP") # PPP page
def showPPP():

	if session.get('logged_in') and session["logged_in"]:
		# PPP ids are a combination of location data
		pppCur = mysql.connection.cursor()
		pppQuery = "SELECT uuid, description, id, location, material FROM PPP WHERE id LIKE %s;"
		loc = ""
		if (session.get('region')):
			loc += session['region']
		if (session.get('insula')):
			loc += session['insula']
		if (session.get('property')):
			loc += session['property']
		if (session.get('room')):
			loc += session['room']

		if loc != "":
			loc += "%"

		pppCur.execute(pppQuery, [loc])
		data = pppCur.fetchall()
		pppCur.close()

		dataplustrans, indices = dataTranslate(data)

		ppp = arc = ""

		if (session.get('carryoverPPP')):
			ppp = session['carryoverPPP']

		for a,d in session['ARClist'].items():
			if d['current']:
				arc = a

		return render_template('PPP.html',
			catextppp=session['carryoverPPP'], dbdata = dataplustrans, indices = indices, arc=arc,
			region=session['region'], insula=session['insula'], property=session['property'], room=session['room'])

	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)



@app.route('/cleardata') #Start over, redirects to home page
def clearData():
	session['carryoverPPP'] = ""
	session['carryoverPPM'] = ""
	session['carryoverPPMImgs'] = []
	session['carryoverPinP'] = ""
	session['carryoverPPPids'] = []
	session['carryoverPPMids'] = []
	session['carryoverPPMImgsids'] = []

	session['arc'] = ""
	session['region'] = ""
	session['insula'] = ""
	session['property'] = ""
	session['room'] = ""

	session['gdoc'] = ""

	files = glob.glob('static/images/*')
	for f in files:
		try:
			os.remove(f)
		except OSError as e:
			print("Error: %s : %s" % (f, e.strerror))

	return render_template('index.html')

if __name__ == "__main__":
	app.run()
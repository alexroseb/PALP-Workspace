from __future__ import print_function
from flask import Flask, render_template, session, json, request, redirect, flash
from flask_mysqldb import MySQL
from google.cloud import translate_v2 as translate
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
											  "pinpimgs": [],
											  "ppmimgs": [],
											  "notes": "",
											  "done": False,
											  "current": False,
											  "trackerindex": l}
			if links[l]:
				session['ARClist'][arclist[l]]["link"] = links[l]

	for a,v in session['ARClist'].items():
		is_art = "no"
		is_plaster = "no"
		pinpCur = mysql.connection.cursor()
		pinpQuery = "SELECT * FROM `PinP_preq` WHERE ARC=" + a +" OR other_ARC LIKE '%" + a + "%';"
		pinpCur.execute(pinpQuery)
		pinpdata = pinpCur.fetchall()
		pinpCur.close()
		for d in pinpdata:
			v["pinpimgs"].append(d[0])
			if d[1] == "maybe" and is_art == "no":
				is_art = "maybe"
			if d[1] == "yes" and (is_art == "no" or is_art == "maybe"):
				is_art = "yes"
			if d[2] == "maybe" and is_plaster == "no":
				is_plaster = "maybe"
			if d[2] == "yes" and (is_plaster == "no" or is_plaster == "maybe"):
				is_plaster = "yes"

		ppmCur = mysql.connection.cursor()
		ppmQuery = "SELECT * FROM `PPM_preq` WHERE ARC=" + a +" OR other_ARC LIKE '%" + a + "%';"
		ppmCur.execute(ppmQuery)
		ppmdata = ppmCur.fetchall()
		ppmCur.close()
		for d in ppmdata:
			v["ppmimgs"].append(d[0])
			if d[1] == "maybe" and is_art == "no":
				is_art = "maybe"
			if d[1] == "yes" and (is_art == "no" or is_art == "maybe"):
				is_art = "yes"
			if d[2] == "maybe" and is_plaster == "no":
				is_plaster = "maybe"
			if d[2] == "yes" and (is_plaster == "no" or is_plaster == "maybe"):
				is_plaster = "yes"

		v["is_art"] = is_art
		v["is_plaster"] = is_plaster

	return redirect('/ARCs')

@app.route('/ARCs')
def chooseARCs():
	return render_template("chooseARCs.html", arcs = session['ARClist'], 
		                   region=session['region'], insula=session['insula'], 
		                   property=session['property'], room=session['room'])

@app.route('/makedoc/<chosenarc>')
def makedoc(chosenarc):
	session['ARClist'][chosenarc]['current'] = True
	if 'http' not in session['ARClist'][chosenarc]['link']:
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
			if len(session['insula']) < 2:
				loc += "0" + session['insula']
			else:
				loc += session['insula']
		if (session.get('property')):
			if len(session['property']) < 2:
				loc += "0" + session['property']
			else:
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

@app.route('/ppp-reviewed')
def pppReviewed():
	strargs = request.args['data'].replace("[", "").replace("]", "")
	pppCur = mysql.connection.cursor()
	pppQuery = "UPDATE PPP SET reviewed=1 WHERE uuid in (" + strargs + ") ;"
	pppCur.execute(pppQuery)
	mysql.connection.commit()
	pppCur.close()

	return redirect('/PPP')

#When items are changed via update form, update database
@app.route('/update-ppp', methods=['POST'])
def updatePPP():
	pppCur = mysql.connection.cursor()
	dictargs = request.form.to_dict()
	for k, v in dictargs.items():
		vrep = v.replace('\n', ' ').replace('\r', ' ').replace('\'', "\\'")
		sep = k.split("_")
		print(sep[0])
		pppQuery = "INSERT INTO PPP(`uuid`) SELECT * FROM ( SELECT '" + sep[0] + "' ) AS tmp WHERE NOT EXISTS ( SELECT 1 FROM PPP WHERE `uuid` = '" + sep[0] + "' ) LIMIT 1;"
		pppCur.execute(pppQuery)
		mysql.connection.commit()
		if sep[1] == "a":
			pppQueryA = "UPDATE PPP SET `id` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryA)
		if sep[1] == "b":
			pppQueryB = "UPDATE PPP SET `location` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryB)
		if sep[1] == "c":
			pppQueryC = "UPDATE PPP SET `material` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryC)
		if sep[1] == "d":
			pppQueryD = "UPDATE PPP SET `description` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryD)
	mysql.connection.commit()
	pppCur.close()

	return redirect('/PPP')

@app.route('/carryover-button') #Carryover button found on multiple pages
def carryover_button():
	if (request.args.get('catextppp')):
		strargs = request.args['catextppp'].replace("[", "").replace("]", "")
		if (session.get('carryoverPPPids')):
			session['carryoverPPPids'] += strargs.split(",")
		else:
			session['carryoverPPPids'] = strargs.split(",")
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPP WHERE uuid in (" + strargs + ") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			if d[1] == 1:
				dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "; "

		if (session.get('carryoverPPP')):
			session['carryoverPPP'] += "; " + dataCopy
		else:
			session['carryoverPPP'] = dataCopy

	if (request.args.get('catextppm')):
		strargs = request.args['catextppm'].replace("[", "").replace("]", "")
		if (session.get('carryoverPPMids')):
			session['carryoverPPMids'] += strargs.split(",")
		else:
			session['carryoverPPMids'] = strargs.split(",")
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT translated_text, reviewed FROM PPM WHERE id in (" + strargs + ") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		if dataList[1] == 1:

			if (session.get('carryoverPPM')):
				session['carryoverPPM'] += "; " + dataList[0]
			else:
				session['carryoverPPM'] = dataList[0]

	if (request.args.get('catextpinp')):
		pinpCur = mysql.connection.cursor()
		pinpQuery = 'UPDATE `PinP` SET `already_used` = 1 where `id_box_file` in (' + request.args['catextpinp'] +');'
		pinpCur.execute(pinpQuery)
		mysql.connection.commit()
		pinpCur.close()
		if (session.get('carryoverPinP')):
			session['carryoverPinP'] += "; " + request.args['catextpinp']
		else:
			session['carryoverPinP'] = request.args['catextpinp']

	if (request.args.get('catextppp')):
		return redirect("/PPM")

	if (request.args.get('catextppm')):
		return redirect("/data")

	if (request.args.get('catextpinp')):
		return redirect("/PPP")

	return redirect("/data")


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
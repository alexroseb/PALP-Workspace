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

scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
scoped_gs = tr_credentials.with_scopes(scopes)
sheets_client = build('sheets', 'v4', credentials=scoped_gs)
sheet = sheets_client.spreadsheets()
tracking_ws = "1EdnoFWDpd38sznIrqMplmFwDMHlN7UATGEEIUsxpZdU" #TEMP: so I don't mess up Sebastian
ranges = "Workflow_Tracking!A3:S87077"

drive_client = build('drive', 'v3', credentials=scoped_gs)

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

#Roman numeral utility
def toRoman(data):
	romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
	if data.isnumeric():
		romin = int(data) - 1
	else:
		romin = 0
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

def pullPre():
	gsheet = sheet.values().get(spreadsheetId=tracking_ws, range=ranges, majorDimension="COLUMNS").execute()
	values = gsheet.get('values', [])
	links = values[10]
	dones = values[17]
	artsDW = values[11]

	for a,v in session['ARClist'].items():
		is_art = "no"
		is_plaster = "no"
		pinpCur = mysql.connection.cursor()
		pinpQuery = "SELECT * FROM `PinP_preq` WHERE `ARC`='" + a +"' OR `other_ARC` LIKE '%" + a + "%';"
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
			v["notes"] += d[5]

		ppmCur = mysql.connection.cursor()
		ppmQuery = "SELECT * FROM `PPM_preq` WHERE `ARC`='" + a +"' OR `other_ARC` LIKE '%" + a + "%';"
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
			v["notes"] += d[5]

		v["is_art"] = is_art
		v["is_plaster"] = is_plaster

		l = v["trackerindex"]
		if links[l]:
			v["link"] = links[l]
		if dones[l]:
			v["done"] = True
		if "DW" in artsDW[l]:
			v["noart"] = True

@app.route('/init', methods=['POST']) #Form submitted from home page
def init():
	session['carryoverPPP'] = ""
	session['carryoverPPPids'] = []
	session['region'] = ""
	session['insula'] = ""
	session['property'] = ""
	session['room'] = ""


	if (request.form.get('region')):
		if request.form['region']:
			session['region'] = request.form['region']
		
	if (request.form.get('insula')):
		if request.form['insula']:
			session['insula'] = request.form['insula']

	if (request.form.get('property')):
		if request.form['property']:
			session['property'] = request.form['property']

	if (request.form.get('room')):
		if request.form['room']:
			session['room'] = request.form['room']

	prop = session['property']
	if session['property'].isalpha():
		prop += "1"
	elif len(session['property']) < 2:
		prop = "0" + prop
	ins = session['insula']
	if len(session['insula']) < 2:
		ins = "0" + ins
	building = toRoman(session['region']) + ins + prop + session['room']

	session['ARClist'] = {}
	session['current'] = ""

	gsheet = sheet.values().get(spreadsheetId=tracking_ws, range=ranges, majorDimension="COLUMNS").execute()
	values = gsheet.get('values', [])
	locationlist = values[0]
	arclist = values[6]

	for l in range(len(locationlist)):
		if locationlist[l].startswith(building):
			session['ARClist'][arclist[l]] = {"link": "None", 
											  "is_art": "Not defined",
											  "is_plaster": "Not defined",
											  "pinpimgs": [],
											  "ppmimgs": [],
											  "notes": "",
											  "done": False,
											  "noart": False,
											  "trackerindex": l}

	return redirect('/ARCs')

@app.route('/ARCs')
def chooseARCs():
	if session.get('logged_in') and session["logged_in"]:
		pullPre()
		return render_template("chooseARCs.html", arcs = session['ARClist'], 
			                   region=session['region'], insula=session['insula'], 
			                   property=session['property'], room=session['room'])
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)

@app.route('/makedoc/<chosenarc>')
def makedoc(chosenarc):
	session['carryoverPPP'] = ""
	session['carryoverPPPids'] = []	
	session['current'] = chosenarc
	
	return redirect('/PPP')

@app.route("/PPP") # PPP page
def showPPP():

	if session.get('logged_in') and session["logged_in"]:
		inswithz = propwithz = ""

		# PPP ids are a combination of location data
		pppCur = mysql.connection.cursor()
		pppQuery = "SELECT uuid, description, id, location, material FROM PPP WHERE id LIKE %s;"
		loc = ""
		if (session.get('region')):
			loc += session['region']
		if (session.get('insula')):
			if len(session['insula']) < 2:
				loc += "0" + session['insula']
				inswithz = "0" + session['insula']
			else:
				loc += session['insula']
				inswithz = session['insula']
		if (session.get('property')):
			if len(session['property']) < 2:
				loc += "0" + session['property']
				propwithz = "0" + session['property']
			else:
				loc += session['property']
				propwithz = session['property']
		if (session.get('room')):
			loc += session['room']

		if loc != "":
			loc += "%"

		pppCur.execute(pppQuery, [loc])
		data = pppCur.fetchall()
		pppCur.close()

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

			arcCur = mysql.connection.cursor()
			arcQuery = 'SELECT ARCs FROM PPP_desc WHERE uuid = "' +d[0] +'";'
			arcCur.execute(arcQuery)
			newarcs = arcCur.fetchall()
			arcCur.close()
			if len(newarcs) > 0:
				dlist.append(newarcs[0][0])
			else:
				dlist.append("")

			dataplustrans.append(dlist)


		return render_template('PPP.html',
			catextppp=session['carryoverPPP'], dbdata = dataplustrans, indices = indices, arc=session['current'],
			region=session['region'], insula=inswithz, property=propwithz, room=session['room'])

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

@app.route("/associated") # PPM and PinP page
def showAssociated():

	if session.get('logged_in') and session["logged_in"]:
		pullPre()
		current = session['current']
		d = session['ARClist'][current]
		totpinp = []
		for p in d['pinpimgs']:
			assocCur = mysql.connection.cursor()
			assocQuery = "SELECT DISTINCT `archive_id`, `id_box_file`, `img_alt` FROM `PinP` WHERE `archive_id` = '"+str(p)+"' ORDER BY `img_url` "
			assocCur.execute(assocQuery)
			all0 = assocCur.fetchall()
			totpinp.append(all0)
			filename = str(all0[0][1]) + ".jpg"
			if not os.path.exists("static/images/"+filename):
				try:
					thumbnail = box_client.file(all0[0][1]).get_thumbnail(extension='jpg', min_width=200)
				except boxsdk.BoxAPIException as exception:
					thumbnail = exception.message
				with open(os.path.join("static/images",filename), "wb") as f:
					f.write(thumbnail)
			assocCur.close()
		totppm = []
		for p in d['ppmimgs']:
			assocCur = mysql.connection.cursor()
			assocQuery = "SELECT DISTINCT `id`, `image_id`, `translated_text` FROM `PPM` WHERE `id` = '"+str(p)+"'"
			assocCur.execute(assocQuery)
			all0 = assocCur.fetchall()
			totppm.append(all0)
			filename = str(all0[0][1]) + ".jpg"
			if not os.path.exists("static/images/"+filename):
				try:
					thumbnail = box_client.file(all0[0][1]).get_thumbnail(extension='jpg', min_width=200)
				except boxsdk.BoxAPIException as exception:
					thumbnail = exception.message
				with open(os.path.join("static/images",filename), "wb") as f:
					f.write(thumbnail)
			assocCur.close()
		return render_template('associated.html', arc=session['current'],
			region=session['region'], insula=session['insula'], property=session['property'], room=session['room'],
			totpinp=totpinp, totppm=totppm)

	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)

@app.route('/descriptions') #Copying data from workspace to Google Sheet 
def showDescs():
	if session.get('logged_in') and session["logged_in"]:
		pullPre()

		current = session['current']
		gdoc = session['ARClist'][current]['link']

		if 'http' not in gdoc:
		# Copy template spreadsheet
			template_spreadsheet_id = "1u7QrUrLg2eftFvzC4OvfohQt88A5mIsFBka6I4ELrUA"
			request_body = { "name": "Workspace_4_" + chosenarc, "parents":['1gJcDYgU53UqqQdUEJl_mb6LgMwxNiqEV']}
			response = drive_client.files().copy(fileId = template_spreadsheet_id, body=request_body, supportsAllDrives = True).execute()
			newID = response['id']

			#Update Workflow Tracker
			newrange = "Workflow_Tracking!K"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
			new_request = {"values": [["https://docs.google.com/spreadsheets/d/" + newID]]}
			updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="USER_ENTERED").execute()

			#Put in link
			session['ARClist'][chosenarc]['link'] = "https://docs.google.com/spreadsheets/d/" + newID
			drive_client.permissions().create(body={"role":"writer", "type":"anyone"}, fileId=newID).execute()
			drive_client.permissions().create(body={"role":"owner", "type":"user", "emailAddress": "abrenon3@gmail.com"}, transferOwnership = True, fileId=newID).execute()

		d = session['ARClist'][current]
		totpinp = []
		for p in d['pinpimgs']:
			assocCur = mysql.connection.cursor()
			assocQuery = "SELECT DISTINCT `img_alt` FROM `PinP` WHERE `archive_id` = '"+str(p)+"' ORDER BY `img_url` "
			assocCur.execute(assocQuery)
			all0 = assocCur.fetchall()
			for a in all0:
				totpinp.append(a[0])
		totppm = []
		for p in d['ppmimgs']:
			assocCur = mysql.connection.cursor()
			assocQuery = "SELECT DISTINCT `translated_text` FROM `PPM` WHERE `id` = '"+str(p)+"'"
			assocCur.execute(assocQuery)
			all0 = assocCur.fetchall()
			for a in all0:
				totppm.append(a[0])

		carryoverpinp = "; ".join(totpinp)
		carryoverppm = "; ".join(totppm)

		return render_template('descs.html',
			carryoverPPP=session['carryoverPPP'], carryoverPPM = carryoverppm, carryoverPinP = carryoverpinp,
			region=session['region'], insula=session['insula'], property=session['property'], room=session['room'], gdoc=gdoc, 
			arc = current)
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)


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

		date = datetime.now().strftime("%Y-%m-%d")
		for i in strargs.split(","):
			addCur = mysql.connection.cursor()
			addQuery = 'INSERT INTO `PPP_desc` (uuid, ARCs, date_added) VALUES (' +i+',"'+session["current"]+'","'+date+'") ON DUPLICATE KEY UPDATE `ARCs` = CONCAT(`ARCs`,", ","'+ session["current"] + '"), `date_added` = "' + date +'";'
			addCur.execute(addQuery)
			addCur.close()

		dataCopy = ""
		for d in dataList:
			if d[1] == 1:
				dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "; "

		if (session.get('carryoverPPP')):
			session['carryoverPPP'] += "; " + dataCopy
		else:
			session['carryoverPPP'] = dataCopy
		return redirect("/associated")
	else:
		return redirect("/PPP")

@app.route('/help') #Help page - the info here is in the HTML
def help():
	return render_template('help.html')

@app.route('/noart')
def noart():
	#Update the tracker "art" column to say "No from DW"

	chosenarc = session['current']
	newrange = "Workflow_Tracking!L"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
	new_request = {"values": [["No from DW"]]}
	updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="RAW").execute()

	return redirect('/ARCs')

@app.route('/done')
def done():
	#Update Workflow Tracker
	chosenarc = session['current']
	newrange = "Workflow_Tracking!R"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
	new_request = {"values": [[datetime.now().strftime("%m/%d/%Y")]]}
	updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="RAW").execute()

	return redirect("/")

if __name__ == "__main__":
	app.run()
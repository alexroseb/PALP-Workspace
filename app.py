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
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from markupsafe import escape

# Using sentry to log errors
sentry_sdk.init(
    dsn="https://5ebc9319ed40454993186c71e8c35553@o493026.ingest.sentry.io/5561383",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)

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
tracking_ws = "1F4nXX1QoyV1miaRUop2ctm8snDyov6GNu9aLt9t3a3M" 
ranges = "Workflow_Tracking!A3:S87078"

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
	"""
	Roman numeral utility
	:param data: Arabic number to be converted (must be between 1 and 9)
	:type data: int
	:returns romreg: Roman numeral 
	:type romreg: str
		
	"""
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

@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

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
	links = values[11]
	dones = values[18]
	artsDW = values[12]

	for a,v in session['ARClist'].items():
		is_art = "no"
		is_plaster = "no"
		v["pinpimgs"] = []
		v["ppmimgs"] = []
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
		if "No from DW" in artsDW[l]:
			v["noart"] = True
		if "Unknown from DW" in artsDW[l]:
			v["unknown"] = True

		arcCur = mysql.connection.cursor()
		arcQuery = 'SELECT uuid FROM PPP_desc WHERE ARCs LIKE "%' + a +'%";'
		arcCur.execute(arcQuery)
		newarcs = arcCur.fetchall()
		v['ppps'] = []
		if len(newarcs) > 0:
			for n in newarcs:
				v['ppps'].append(n[0])

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
		else:
			session['insula'] = ""

	if (request.form.get('property')):
		if request.form['property']:
			session['property'] = request.form['property']
		else:
			session['property'] = ""

	if (request.form.get('room')):
		if request.form['room']:
			session['room'] = request.form['room']
		else:
			session['room'] = ""
	# prop = session['property']
	# if session['property'].isalpha():
	# 	prop += "1"
	# elif len(session['property']) < 2:
	# 	prop = "0" + prop
	# ins = session['insula']
	# if len(session['insula']) < 2:
	# 	ins = "0" + ins
	# building = toRoman(session['region']) + ins + prop + session['room']

	building = "r" + str(session['region']) + "-i"+str(session['insula']) + "-p" + session['property'] + "-space-" + session['room']
	session['ARClist'] = {}
	session['current'] = ""

	gsheet = sheet.values().get(spreadsheetId=tracking_ws, range=ranges, majorDimension="COLUMNS").execute()
	values = gsheet.get('values', [])
	locationlist = values[1]
	arclist = values[7]

	for l in range(len(locationlist)):
		places = locationlist[l].split("-")
		if (places[0] == "r" + str(session['region'])) and ((places[1] == "i" +str(session['insula'])) or session['insula'] == "") and ((places[2] == "p" +str(session['property'])) or session['property'] == "") and (("-".join(places[3:]) == "space-" +str(session['room'])) or session['room'] == ""):
		#if locationlist[l].startswith(building):
			session['ARClist'][arclist[l]] = {"link": "None", 
											  "is_art": "Not defined",
											  "is_plaster": "Not defined",
											  "pinpimgs": [],
											  "ppmimgs": [],
											  "notes": "",
											  "done": False,
											  "noart": False,
											  "unknown": False,
											  "trackerindex": l, 
											  "ppps": []}

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
		pullPre()
		inswithz = propwithz = ""

		pppCur = mysql.connection.cursor()
		rm = ""
		if session['room']:
			rm = "' and `Room` = '" +session['room']
		pppQuery = "SELECT uuid, description, id, location, material, Room FROM PPP WHERE `Region` = '" +session['region']+ "' and `Insula` = '" +session['insula']+ "' and `Doorway` = '" +session['property']+ rm+"';"

		pppCur.execute(pppQuery)
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

		current = session['current']
		v = session['ARClist'][current]
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPP WHERE uuid in ('" + "','".join(v["ppps"]) + "') ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "; "

		session['carryoverPPP'] = dataCopy


		return render_template('PPP.html',
			catextppp=session['carryoverPPP'], dbdata = dataplustrans, indices = indices, arc=session['current'],
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
	date = datetime.now().strftime("%Y-%m-%d")
	for k, v in dictargs.items():
		vrep = v.replace('\n', ' ').replace('\r', ' ').replace('\'', "\\'")
		vrep = escape(vrep)
		sep = k.split("_")
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
		if sep[1] == "e":
			pppQueryE = "UPDATE PPP SET `Region` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryE)
		if sep[1] == "f":
			pppQueryF = "UPDATE PPP SET `Insula` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryF)
		if sep[1] == "g":
			pppQueryG = "UPDATE PPP SET `Doorway` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryG)
		if sep[1] == "h":
			pppQueryH = "UPDATE PPP SET `Room` = '" + vrep + "' WHERE `uuid` = '" + sep[0] + "';"
			pppCur.execute(pppQueryH)
		if sep[1] == "i":
			pppQueryI = 'INSERT INTO `PPP_desc` (uuid, ARCs, date_added) VALUES ("' +sep[0]+'","'+vrep+'","'+date+'") ON DUPLICATE KEY UPDATE `ARCs` = "'+ vrep + '", `date_added` = "' + date +'";'
			pppCur.execute(pppQueryI)
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
					thumbnail = bytes(exception.message, 'utf-8')
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
					thumbnail = bytes(exception.message, 'utf-8')
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
			template_spreadsheet_id = "13M3sk4RAOy2Jlq86ECdwR8m11MsOaUNF1unbP6yQF-g"
			request_body = { "name": "Workspace_5_" + current, "parents":['1G_ZH-20qmxudaymDXMPe0wT4w_C_r00Q']}
			response = drive_client.files().copy(fileId = template_spreadsheet_id, body=request_body, supportsAllDrives = True).execute()
			newID = response['id']

			#Update Workflow Tracker
			newrange = "Workflow_Tracking!L"+ str(session['ARClist'][current]['trackerindex']+3)
			new_request = {"values": [["https://docs.google.com/spreadsheets/d/" + newID]]}
			updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="USER_ENTERED").execute()

			#Put in link
			session['ARClist'][current]['link'] = "https://docs.google.com/spreadsheets/d/" + newID
			
			auth_users = ['smastroianni@umass.edu', 'fdipietro@umass.edu', 'bmai@umass.edu', 'nicmjohnson@umass.edu', 'mcknapp@umass.edu', 'dbeason@umass.edu', 'lfield@umass.edu', 'tbernard@umass.edu', 'mhoffenberg@umass.edu', 'gsharaga@umass.edu', 'droller@umass.edu', 'shazizi@umass.edu', 'laurejt@umass.edu', 'abrenon@umass.edu', 'epoehler@classics.umass.edu', 'epoehler@gmail.com', 'palp-workspace@my-project-1537454316408.iam.gserviceaccount.com', 'plod@umass.edu', 'plodAD97@gmail.com']
			for u in auth_users:
				drive_client.permissions().create(body={"role":"writer", "type":"user", 'emailAddress': u, 'sendNotificationEmail': False}, fileId=newID).execute()
			drive_client.permissions().create(body={"role":"owner", "type":"user", "emailAddress": "plodAD79@gmail.com"}, transferOwnership = True, fileId=newID).execute()
		gdoc = session['ARClist'][current]['link']
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

		current = session['current']
		v = session['ARClist'][current]
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPP WHERE uuid in ('" + "','".join(v["ppps"]) + "') ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "; "

		session['carryoverPPP'] = dataCopy


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
		date = datetime.now().strftime("%Y-%m-%d")
		for i in strargs.split(","):
			addCur = mysql.connection.cursor()
			addQuery = 'INSERT INTO `PPP_desc` (uuid, ARCs, date_added) VALUES (' +i+',"'+session["current"]+'","'+date+'") ON DUPLICATE KEY UPDATE `ARCs` = "'+ session["current"] + '", `date_added` = "' + date +'";'
			#now just replaces existing
			#addQuery = 'INSERT INTO `PPP_desc` (uuid, ARCs, date_added) VALUES (' +i+',"'+session["current"]+'","'+date+'");'
			addCur.execute(addQuery)
			addCur.close()

		current = session['current']
		v = session['ARClist'][current]
		arcCur = mysql.connection.cursor()
		arcQuery = 'SELECT uuid FROM PPP_desc WHERE ARCs LIKE "%' + current +'%";'
		arcCur.execute(arcQuery)
		newarcs = arcCur.fetchall()
		v['ppps'] = []
		if len(newarcs) > 0:
			for n in newarcs:
				v['ppps'].append(n[0])

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
	newrange = "Workflow_Tracking!M"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
	new_request = {"values": [["No from DW"]]}
	updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="RAW").execute()

	return redirect('/ARCs')

@app.route('/unknownart')
def unknownart():
	#Update the tracker "art" column to say "Unknown from DW"

	chosenarc = session['current']
	newrange = "Workflow_Tracking!M"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
	new_request = {"values": [["Unknown from DW"]]}
	updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="RAW").execute()

	return redirect('/ARCs')

@app.route('/done', methods=['POST', 'GET'])
def done():
	#Update Workflow Tracker
	db = request.form['pinporppm']
	imgid = request.form.get("hero")
	if db == "PinP_preq":
		dbid = "archive_id"
	if db == "PPM_preq":
		dbid = "id"
	date = datetime.now().strftime("%Y-%m-%d")
	ppmCur = mysql.connection.cursor()
	ppmQuery = 'INSERT INTO `'+db+'` ('+dbid+', hero_image, date_added) VALUES ('+ imgid +',"1",'+ date +') ON DUPLICATE KEY UPDATE `hero_image` = "1", `date_added` = "' + date +'";'
	ppmCur.execute(ppmQuery)
	mysql.connection.commit()
	ppmCur.close()
	chosenarc = session['current']
	newrange = "Workflow_Tracking!S"+ str(session['ARClist'][chosenarc]['trackerindex']+3)
	new_request = {"values": [[datetime.now().strftime("%m/%d/%Y")]]}
	updatelink = sheet.values().update(spreadsheetId=tracking_ws, range=newrange, body=new_request, valueInputOption="RAW").execute()

	return redirect("/ARCs")

@app.route("/PPP-single") # Edit one PPP at a time
def showPPPSingle():
# put into URL search by PPP id
# "next" button leads you to next uuid numerically
	if session.get('logged_in') and session["logged_in"]:

		pppCur = mysql.connection.cursor()
		# catch error - flash "no id"
		if (request.args.get('uuid')):
			pppQuery = "SELECT uuid, id, location, material, description, condition_ppp, style, bibliography, photo_negative FROM PPP WHERE `uuid` = '"+str(request.args['uuid'])+"';"
			try:
				pppCur.execute(pppQuery)
				data = pppCur.fetchall()
			except Exception as exception:
				data = ['error', 'Unique ID', request.args['uuid']]
		elif (request.args.get('id')):
			pppQuery = "SELECT uuid, id, location, material, description, condition_ppp, style, bibliography, photo_negative FROM PPP WHERE `id` = '"+str(request.args['id'])+"';"
			try:
				pppCur.execute(pppQuery)
				data = pppCur.fetchall()
			except Exception:
				data = ['error', 'PPP ID', request.args['id']]
		else:
		    data = ['error', 'Nothing - ', 'please add ?id= or ?uuid=']
		pppCur.close()

		return render_template('PPP-single.html', dbdata = data, 
			region=session['region'], insula=session['insula'], property=session['property'], room=session['room'])

	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)

#When items are changed via update form, update database
@app.route('/update-ppp-edit', methods=['POST'])
def updatePPPEdit():
	pppCur = mysql.connection.cursor()
	dictargs = request.form.to_dict()
	date = datetime.now().strftime("%Y-%m-%d")
	sep = dictargs['uuid']
	for k, v in dictargs.items():
		pppQuery = "INSERT INTO PPP(`uuid`) SELECT * FROM ( SELECT '" + sep + "' ) AS tmp WHERE NOT EXISTS ( SELECT 1 FROM PPP WHERE `uuid` = '" + sep + "' ) LIMIT 1;"
		pppCur.execute(pppQuery)
		mysql.connection.commit()
		vrep = v.replace('\n', ' ').replace('\r', ' ').replace('\'', "\\'")
		if k == "PPPID":
			pppQueryA = "UPDATE PPP SET `id` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryA)
		if k == "location":
			pppQueryB = "UPDATE PPP SET `location` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryB)
		if k == "material":
			pppQueryC = "UPDATE PPP SET `material` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryC)
		if k == "description":
			pppQueryD = "UPDATE PPP SET `description` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryD)
		if k == "condition":
			pppQueryE = "UPDATE PPP SET `condition_ppp` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryE)
		if k == "style":
			pppQueryF = "UPDATE PPP SET `style` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryF)
		if k == "bibliography":
			pppQueryG = "UPDATE PPP SET `bibliography` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryG)
		if k == "negative":
			pppQueryH = "UPDATE PPP SET `photo_negative` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryH)
		if k == "region":
			pppQueryI = "UPDATE PPP SET `Region` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryI)
		if k == "insula":
			pppQueryJ = "UPDATE PPP SET `Insula` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryJ)
		if k == "doorway":
			pppQueryK = "UPDATE PPP SET `Doorway` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryK)
		if k == "room":
			pppQueryL = "UPDATE PPP SET `Room` = '" + vrep + "' WHERE `uuid` = '" + sep + "';"
			pppCur.execute(pppQueryL)
	mysql.connection.commit()
	pppCur.close()

	if sep.startswith('new'):
		nextidint = int(sep[3:]) + 1
		nextid = "new"+str(nextidint)
	else:
		nextidint = int(sep) + 1
		nextid = str(nextidint)
	# redirect will contain parameters
	return redirect('/PPP-single?uuid='+nextid)

if __name__ == "__main__":
	app.run()
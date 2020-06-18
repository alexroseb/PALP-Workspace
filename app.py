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

#Google Translate credentials
tr_credentials = service_account.Credentials.from_service_account_file("My Project-1f2512d178cb.json")
translate_client = translate.Client(credentials=tr_credentials)

#Google Sheets credentials
scopes = ['https://www.googleapis.com/auth/spreadsheets']
scoped_gs = tr_credentials.with_scopes(scopes)
sheets_client = build('sheets', 'v4', credentials=scoped_gs)

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
	arc = ""

	if (session.get('arc')):
		arc = session['arc']

	return render_template('index.html', arc=arc, error="")

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
	return render_template('index.html', arc="", error=error)

@app.route('/init', methods=['POST']) #Form submitted from home page
def init():
	arc = request.form['arc']
	session['arc'] = arc

	#Connect to Google Sheets
	sheet = sheets_client.spreadsheets()
	tracking_ws = "1F4nXX1QoyV1miaRUop2ctm8snDyov6GNu9aLt9t3a3M"
	ranges = "Workflow_Tracking!A3:L87075"
	gsheet = sheet.values().get(spreadsheetId=tracking_ws, range=ranges, majorDimension="COLUMNS").execute()
	values = gsheet.get('values', [])

	arclist = values[6] #Column G
	if arc in arclist:
		arcind = arclist.index(arc)
		session['gdoc'] = values[10][arcind] #Column K
		s = values[0][arcind]
		s = re.sub("IX","9",s)
		s = re.sub("IV","4",s)
		s = re.sub("VIII","8",s)
		s = re.sub("VII","7",s)
		s = re.sub("VI","6",s)
		s = re.sub("V","5",s)
		s = re.sub("III","3",s)
		s = re.sub("II","2",s)
		s = re.sub("I","1",s)

		session['region'] = s[0]
		session['insula'] = s[1:3]
		session['property'] = s[3:5]
		session['room'] = s[5:]

	else:
		return render_template('index.html', arc=arc, error="I'm sorry, that's an invalid ARC. Please try again.")

	done_ws = "1HaKXGdS-ZS42HiK8d1KeeSdC199MdxyP42QqsUlzZBQ"
	donesheet = sheet.values().get(spreadsheetId=done_ws, range="Sheet1", majorDimension="COLUMNS").execute()
	donevalues = donesheet.get('values', [])
	donelist = donevalues[2]
	if arc in donelist:
		arcind = donelist.index(arc)
		arcrange = str(arcind) + ":" + str(arcind)
		arcsheet = sheet.values().get(spreadsheetId=done_ws, range=arcrange).execute()
		arcvalues = arcsheet.get('values', [])

		session['carryoverPPP'] = arcvalues[0][7]
		session['carryoverPPM'] = arcvalues[0][9]
		session['carryoverPinP'] = arcvalues[0][11]
		session['carryoverPPPids'] = arcvalues[0][6].split(",")
		session['carryoverPPMids'] = arcvalues[0][8].split(",")
		session['carryoverPPMImgsids'] = arcvalues[0][10].split(",")

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

		ppp = reg = ins = prop = room = iframeurl = ""

		#each region has its own PDF doc
		if (session.get('region')):
			reg = session['region']
			if session['region'] == "1":
				iframeurl = "https://umass.app.box.com/embed/s/t1a98m2my6eoxjciwqa0fpcmth2zwe3b?sortColumn=date&view=list"
			if session['region'] == "2":
				iframeurl = "https://umass.app.box.com/embed/s/j8ln3zdz61rh9aiszhhs3b0pn20dv2ky?sortColumn=date&view=list"
			if session['region'] == "3":
				iframeurl = "https://umass.app.box.com/embed/s/mgki1vhjmijzpcjqpb37vucfozqhr6kh?sortColumn=date&view=list"
			if session['region'] == "4":
				iframeurl = ""
			if session['region'] == "5":
				iframeurl = "https://umass.app.box.com/embed/s/398sfo7og26lqms6a7cynwczomujt7b8?sortColumn=date&view=list"
			if session['region'] == "6":
				iframeurl = "https://umass.app.box.com/embed/s/vi6ysrxgfr4dcoc5x87alu82d2lakua5?sortColumn=date&view=list"
			if session['region'] == "7":
				iframeurl = "https://umass.app.box.com/embed/s/26wkz8v3cqhkrwmeipas1jtuz0eobm3z?sortColumn=date&view=list"
			if session['region'] == "8":
				iframeurl = "https://umass.app.box.com/embed/s/aucwrzc5k7dtm786itiwc4gch91nr83k?sortColumn=date&view=list"
			if session['region'] == "9":
				iframeurl = "https://umass.app.box.com/embed/s/fxiqa4fu8ki1zmf3oiq357fgaiegxd48?sortColumn=date&view=list"
		if (session.get('insula')):
			ins = session['insula']
		if (session.get('property')):
			prop = session['property']
		if (session.get('room')):
			room = session['room']

		if (session.get('carryoverPPP')):
			ppp = session['carryoverPPP']

		return render_template('PPP.html',
			catextppp=ppp, dbdata = dataplustrans, indices = indices,
			region=reg, insula=ins, property=prop, room=room, iframeurl = iframeurl)

	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)

@app.route('/PPM') #PPM page
def showPPM():

	if session.get('logged_in') and session["logged_in"]:

		#PPM data has individual location columns
		ppmCur = mysql.connection.cursor()
		ppmQuery = "SELECT id, description, image_path, region, insula, doorway, room FROM PPM WHERE region LIKE %s AND insula LIKE %s AND doorway LIKE %s AND room LIKE %s ORDER BY `description` ASC;"
		loc = []
		if (session.get('region')):
			loc.append(toRoman(session['region']))
		else:
			loc.append("%")
		if (session.get('insula')):
			ins = session['insula']
			if session['insula'][0] == "0":
				ins = session['insula'].replace("0","")
			loc.append(ins)
		else:
			loc.append("%")
		if (session.get('property')):
			prop = session['property'] 
			if session['property'][0] == "0":
				prop = session['property'].replace("0","")
			loc.append(prop)
		else:
			loc.append("%")
		if (session.get('room')):
			room = session['room'] 
			if session['room'][0] == "0":
				room = session['room'].replace("0","")
			loc.append(room)
		else:
			loc.append("%")

		ppmCur.execute(ppmQuery, loc)
		data = ppmCur.fetchall()

		dataplustrans, indices = dataTranslate(data)

		imgs = []
		for d in data:
			itemid = "0"
			print(d[2])
			searchid = "\"" + d[2] + "\""
			box_id = box_client.search().query(query=searchid, file_extensions=['jpg'], ancestor_folder_ids="97077887697,87326350215", fields=["id", "name"], content_types=["name"])
			for item in box_id:
				if item.name == d[2]:
					itemid = item.id
					imgs.append(itemid)
					print(itemid)
					break
			try:
				thumbnail = box_client.file(itemid).get_thumbnail(extension='jpg', min_width=200)
			except boxsdk.BoxAPIException as exception:
				thumbnail = bytes(exception.message, 'utf-8')
			filename = str(itemid) + ".jpg"
			if not os.path.exists("static/images/"+filename):
				with open(os.path.join("static/images",filename), "wb") as f:
					f.write(thumbnail)
		for x in range(len(dataplustrans)):
			j = dataplustrans[x]
			j.insert(1, imgs[x])
			imgQuery = "UPDATE PPM SET image_id= %s WHERE id = %s ;"
			ppmCur.execute(imgQuery, [imgs[x], j[0]])
			mysql.connection.commit()
		
		ppmCur.close()

		ppm = ppmimg = reg = ins = prop = room = iframeurl = ""

		#each region (theoretically) has its own PDF doc
		if (session.get('region')):
			reg = session['region']
			if session['region'] == "1":
				iframeurl = ""
			if session['region'] == "2":
				iframeurl = ""
			if session['region'] == "3":
				iframeurl = ""
			if session['region'] == "4":
				iframeurl = ""
			if session['region'] == "5":
				iframeurl = ""
			if session['region'] == "6":
				iframeurl = ""
			if session['region'] == "7":
				iframeurl = ""
			if session['region'] == "8":
				iframeurl = ""
			if session['region'] == "9":
				iframeurl = ""
		if (session.get('insula')):
			ins = session['insula']
		if (session.get('property')):
			prop = session['property']
		if (session.get('room')):
			room = session['room']

		if (session.get('carryoverPPM')):
			ppm = session['carryoverPPM']
		if (session.get('carryoverPPMImgs')):
			ppmimg = session['carryoverPPMImgs']

		return render_template('PPM.html',
			catextppm=ppm, catextppmimg=ppmimg, dbdata = dataplustrans, indices = indices,
			region=reg, insula=ins, property=prop, room=room, iframeurl = iframeurl)
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)
	

# When items are marked as reviewed, update database
@app.route('/ppm-reviewed') 
def ppmReviewed():
	strargs = request.args['data'].replace("[", "").replace("]", "")
	ppmCur = mysql.connection.cursor()
	ppmQuery = "UPDATE PPM SET reviewed=1 WHERE id in (" + strargs + ") ;"
	ppmCur.execute(ppmQuery)
	mysql.connection.commit()
	ppmCur.close()

	return redirect('/PPM')

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

@app.route('/update-ppm', methods=['POST'])
def updatePPM():
	ppmCur = mysql.connection.cursor()
	dictargs = request.form.to_dict()
	for k in dictargs:
		krem =  dictargs[k].replace('\n', ' ').replace('\r', ' ').replace('\'', "\\'")
		ppmQuery = "UPDATE PPM SET `description` = '" + krem + "' WHERE id = " + k + ";"
		print(ppmQuery)
		ppmCur.execute(ppmQuery)
	mysql.connection.commit()
	ppmCur.close()

	return redirect('/PPM')

@app.route('/PinP') #PinP page
def showPinP():
	if session.get('logged_in') and session["logged_in"]:

		pinp = reg = ins = prop = room = ""

		pinpCur = mysql.connection.cursor()

		#Join tbl_webpage_images and tbl_box_images on id
		pinpQuery = "SELECT `tbl_webpage_images`.`id` as id, `tbl_box_images`.`id_box_file` as box_id, `tbl_webpage_images`.`img_alt` as description FROM `tbl_webpage_images` left join `tbl_box_images` on `tbl_webpage_images`.`id` = `tbl_box_images`.`id_tbl_webpage_images` left join `tbl_addresses_x` on `tbl_webpage_images`.`id` = `tbl_addresses_x`.`wi_id` left join `tbl_addresses` on `tbl_addresses_x`.`add_id` = `tbl_addresses`.`id` where `tbl_addresses`.`pinp_regio` LIKE %s and `tbl_addresses`.`pinp_insula` LIKE %s  and `tbl_addresses`.`pinp_entrance` LIKE %s ORDER BY wi_id;"

		loc = []
		if (session.get('region')):
			loc.append(toRoman(session['region']))
		else:
			loc.append("%")
		if (session.get('insula')):
			ins = session['insula']
			if session['insula'][0] == "0":
				ins = session['insula'].replace("0","")
			loc.append(ins)
		else:
			loc.append("%")
		if (session.get('property')):
			prop = session['property'] 
			if session['property'][0] == "0":
				prop = session['property'].replace("0","")
			loc.append(prop)
		else:
			loc.append("%")

		pinpCur.execute(pinpQuery, loc)

		data = pinpCur.fetchall()
		pinpCur.close()

		indices = []
		thumbnails = {}
		for d in data:
			indices.append(d[1])
			try:
				thumbnail = box_client.file(d[1]).get_thumbnail(extension='jpg', min_width=200)
			except boxsdk.BoxAPIException as exception:
				thumbnail = exception.message
			filename = str(d[1]) + ".jpg"
			if not os.path.exists("static/images/"+filename):
				with open(os.path.join("static/images",filename), "wb") as f:
					f.write(thumbnail)

		if (session.get('region')):
			reg = session['region']
		if (session.get('insula')):
			ins = session['insula']
		if (session.get('property')):
			prop = session['property']
		if (session.get('room')):
			room = session['room']

		if (session.get('carryoverPinP')):
			pinp = session['carryoverPinP']

		return render_template('PinP.html',
			catextpinp=pinp, dbdata = data, indices = indices, thumbnails = thumbnails,
			region=reg, insula=ins, property=prop, room=room)
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)
	
@app.route('/help') #Help page - the info here is in the HTML
def help():
	reg = ins = prop = room = ""

	if (session.get('region')):
		reg = session['region']
	if (session.get('insula')):
		ins = session['insula']
	if (session.get('property')):
		prop = session['property']
	if (session.get('room')):
		room = session['room']

	return render_template('help.html',
		region=reg, insula=ins, property=prop, room=room)

@app.route('/GIS') #Embedded GIS map
def GIS():
	reg = ins = prop = room = ""

	if (session.get('region')):
		reg = session['region']
	if (session.get('insula')):
		ins = session['insula']
	if (session.get('property')):
		prop = session['property']
	if (session.get('room')):
		room = session['room']

	return render_template('GIS.html',
		region=reg, insula=ins, property=prop, room=room)


@app.route('/descriptions') #Copying data from workspace to Google Sheet 
def showDescs():
	if session.get('logged_in') and session["logged_in"]:

		ppp = ppm = ppmimg = pinp = reg = ins = prop = room = gdoc = ""

		if (session.get('region')):
			reg = session['region']
		if (session.get('insula')):
			ins = session['insula']
		if (session.get('property')):
			prop = session['property']
		if (session.get('room')):
			room = session['room']

		if (session.get('carryoverPPP')):
			ppp = session['carryoverPPP']
		if (session.get('carryoverPPM')):
			ppm = session['carryoverPPM']
		if (session.get('carryoverPPMImgs')):
			ppmimg = session['carryoverPPMImgs']
		if (session.get('carryoverPinP')):
			pinp = session['carryoverPinP']

		if (session.get('gdoc')):
			gdoc = session['gdoc']

		return render_template('descs.html',
			carryoverPPP=ppp, carryoverPPM=ppm, carryoverPPMImgs=ppmimg, carryoverPinP=pinp,
			region=reg, insula=ins, property=prop, room=room, gdoc=gdoc)
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)


@app.route('/data') #Show carried over data
def showCarryover():
	if session.get('logged_in') and session["logged_in"]:

		ppp = ppm = ppmimg = pinp = []
		reg = ins = prop = room = ""

		if (session.get('region')):
			reg = session['region']
		if (session.get('insula')):
			ins = session['insula']
		if (session.get('property')):
			prop = session['property']
		if (session.get('room')):
			room = session['room']

		if (session.get('carryoverPPPids')):
			carryCur = mysql.connection.cursor()
			inn = ', '.join(session['carryoverPPPids'])
			carryQuery = "SELECT id, description FROM PPP WHERE uuid in (" + inn +") ;"
			carryCur.execute(carryQuery)
			dataList = carryCur.fetchall()
			carryCur.close()
			ppp, pppinds = dataTranslate(dataList)
		if (session.get('carryoverPPMids')):
			inn = ', '.join(session['carryoverPPMids'])
			carryCur = mysql.connection.cursor()
			carryQuery = "SELECT id, description, image_id FROM PPM WHERE id in (" + inn +") ;"
			carryCur.execute(carryQuery)
			dataList = carryCur.fetchall()
			carryCur.close()
			session['carryoverPPMImgs'] = []
			for x in dataList:
				session['carryoverPPMImgs'].append(x[2])
			ppm, ppminds = dataTranslate(dataList)		
		if (session.get('carryoverPinP')):
			pp = session['carryoverPinP'].replace(",", ";").replace("\"", "").replace(" ", "")
			pinp = pp.split(";")

		return render_template('imgs.html',
			pppdata=ppp, ppmdata=ppm, ppming=ppmimg, pinpdata = pinp,
			region=reg, insula=ins, property=prop, room=room)
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
		carryQuery = "SELECT description, reviewed FROM PPM WHERE id in (" + strargs + ") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			if d[1] == 1:
				dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "; "

		if (session.get('carryoverPPM')):
			session['carryoverPPM'] += "; " + dataCopy
		else:
			session['carryoverPPM'] = dataCopy

	if (request.args.get('catextpinp')):
		if (session.get('carryoverPinP')):
			session['carryoverPinP'] += "; " + request.args['catextpinp']
		else:
			session['carryoverPinP'] = request.args['catextpinp']

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
	session['carryoverPinPids'] = []

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

@app.route('/savedata') #Copy saved data to Google Sheets
def saveData():

	if session.get('logged_in') and session["logged_in"]:

		now = datetime.now()
		timestamp = now.strftime("%m/%d/%Y, %H:%M:%S")
		queryvars = [timestamp]
		queryvars.append(session['arc'])
		if (session.get('region')):
			queryvars.append(str(session['region']))
		else:
			queryvars.append("")
		if (session.get('insula')):
			queryvars.append(str(session['insula']))
		else:
			queryvars.append("")
		if (session.get('property')):
			queryvars.append(str(session['property']))
		else:
			queryvars.append("")
		if (session.get('room')):
			queryvars.append(str(session['room']))
		else:
			queryvars.append("")

		if (session.get('carryoverPPPids')):
			queryvars.append(str(session['carryoverPPPids']))
		else:
			queryvars.append("")
	#Add in PPP italian, placeholder for now

		if (session.get('carryoverPPP')):
			queryvars.append(str(session['carryoverPPP']))
		else:
			queryvars.append("")

		if (session.get('carryoverPPMids')):
			queryvars.append(str(session['carryoverPPMids']))
		else:
			queryvars.append("")
	#Add in PPM italian, placeholder for now

		if (session.get('carryoverPPM')):
			queryvars.append(str(session['carryoverPPM']))
		else:
			queryvars.append("")


		if (session.get('carryoverPPMImgs')):
			queryvars.append(str(session['carryoverPPMImgs']))
		else:
			queryvars.append("")
		if (session.get('carryoverPinP')):
			queryvars.append(str(session['carryoverPinP']))
		else:
			queryvars.append("")
		if (session.get('gdoc')):
			queryvars.append(str(session['gdoc']))
		else:
			queryvars.append("")

		values = [queryvars]
		print(values)
		body = {
		    'values': values
		}
		ranges = "Sheet1"

		sheet = sheets_client.spreadsheets()
		done_ws = "1HaKXGdS-ZS42HiK8d1KeeSdC199MdxyP42QqsUlzZBQ"
		donesheet = sheet.values().get(spreadsheetId=done_ws, range="Sheet1", majorDimension="COLUMNS").execute()
		donevalues = donesheet.get('values', [])
		donelist = donevalues[2]
		if session['arc'] in donelist:
			arcind = donelist.index(session['arc'])
			ranges = str(arcind) + ":" + str(arcind)

		result = sheet.values().append(spreadsheetId="1HaKXGdS-ZS42HiK8d1KeeSdC199MdxyP42QqsUlzZBQ",range=ranges, valueInputOption="USER_ENTERED", insertDataOption="OVERWRITE", body=body).execute()

		return redirect("/descriptions")
	else:
		error= "Sorry, this page is only accessible by logging in."
		return render_template('index.html', arc="", error=error)

@app.route('/search', methods=['POST']) #Search bar at top of pages
def search():
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
	return redirect(request.referrer)


if __name__ == "__main__":
	app.run()
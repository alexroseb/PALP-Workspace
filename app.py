from __future__ import print_function
from flask import Flask, render_template, session, json, request, redirect
from flask_mysqldb import MySQL
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from googleapiclient.discovery import build
import boxsdk
import json
import re

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
scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
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
	return romreg

@app.route("/") # Home page
def index():
	arc = ""

	if (session.get('arc')):
		arc = session['arc']

	return render_template('index.html', arc=arc, error="")

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

	return redirect('/PPP')

@app.route("/PPP") # PPP page
def showPPP():

	# PPP ids are a combination of location data
	pppCur = mysql.connection.cursor()
	pppQuery = "SELECT id, description FROM PPP WHERE id LIKE %s;"
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

@app.route('/PPM') #PPM page
def showPPM():

	#PPM data has individual location columns
	ppmCur = mysql.connection.cursor()
	ppmQuery = "SELECT id, description FROM PPM WHERE region LIKE %s AND insula LIKE %s AND doorway LIKE %s AND room LIKE %s;"
	loc = []
	if (session.get('region')):
		loc.append(toRoman(session['region']))
	else:
		loc.append("%")
	if (session.get('insula')):
		loc.append(session['insula'])
	else:
		loc.append("%")
	if (session.get('property')):
		loc.append(session['property'])
	else:
		loc.append("%")
	if (session.get('room')):
		loc.append(session['room'])
	else:
		loc.append("%")

	ppmCur.execute(ppmQuery, loc)
	data = ppmCur.fetchall()
	ppmCur.close()

	dataplustrans, indices = dataTranslate(data)

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
	pppQuery = "UPDATE PPP SET reviewed=1 WHERE id in (" + strargs + ") ;"
	pppCur.execute(pppQuery)
	mysql.connection.commit()
	pppCur.close()

	return redirect('/PPP')

#When items are changed via update form, update database
@app.route('/update-ppp', methods=['POST'])
def updatePPP():
	pppCur = mysql.connection.cursor()
	dictargs = request.form.to_dict()
	for k in dictargs:
		pppQuery = "UPDATE PPP SET `description` = '" + dictargs[k] + "' WHERE id = " + k + ";"
		pppCur.execute(pppQuery)
	mysql.connection.commit()
	pppCur.close()

	return redirect('/PPP')

@app.route('/update-ppm', methods=['POST'])
def updatePPM():
	ppmCur = mysql.connection.cursor()
	dictargs = request.form.to_dict()
	for k in dictargs:
		ppmQuery = "UPDATE PPM SET `description` = '" + dictargs[k] + "' WHERE id = " + k + ";"
		ppmCur.execute(ppmQuery)
	mysql.connection.commit()
	ppmCur.close()

	return redirect('/PPM')

@app.route('/PinP') #PinP page
def showPinP():
	pinp = reg = ins = prop = room = ""

	pinpCur = mysql.connection.cursor()
	pinpQuery = "Select tbl_webpage_images.id as wi_id, tbl_webpage_images.img_url as img_url, tbl_webpage_images.azure_img_desc as azure_img_desc, tbl_webpage_images.azure_img_tags as azure_img_tags, tbl_webpage_images.image_hash as image_hash, tbl_webpage_images.img_alt as img_alt, tbl_webpages.folder as folder, tbl_webpages.file_name as file_name from tbl_webpage_images left join tbl_addresses_x on tbl_webpage_images.id = tbl_addresses_x.wi_id left join tbl_addresses on tbl_addresses_x.add_id = tbl_addresses.id left join tbl_webpages on tbl_webpages.id = tbl_webpage_images.id_webpage where tbl_addresses.pinp_regio LIKE %s and tbl_addresses.pinp_insula LIKE %s  and tbl_addresses.pinp_entrance LIKE %s ORDER BY wi_id;"

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
	for d in data:
		indices.append(d[0])

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
		catextpinp=pinp, dbdata = data, indices = indices,
		region=reg, insula=ins, property=prop, room=room)

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

@app.route('/data') #Show carried over data
def showCarryover():
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
		carryQuery = "SELECT id, description FROM PPP WHERE id in (" + inn +") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()
		ppp, pppinds = dataTranslate(dataList)
	if (session.get('carryoverPPMids')):
		inn = ', '.join(session['carryoverPPMids'])
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT id, description FROM PPM WHERE id in (" + inn +") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()
		ppm, ppminds = dataTranslate(dataList)
	if (session.get('carryoverPPMImgsids')):
		ppmimg = session['carryoverPPMImgsids']
	if (session.get('carryoverPinPids')):
		pinp = session['carryoverPinPids']

	file_id = '525898106477'

	try:
		thumbnail = box_client.file(file_id).get_thumbnail(extension='jpg')
	except boxsdk.BoxAPIException as exception:
		thumbnail = exception.code

	return render_template('imgs.html',
		pppdata=ppp, ppmdata=ppm, ppming=ppmimg, pinpdata=pinp, thumbnail=thumbnail,
		region=reg, insula=ins, property=prop, room=room)

@app.route('/carryover', methods=['POST']) #Carryover form found on multiple pages
# Deprecated?
def carryover_text():
	if (request.form.get('catextppp')):
		if (session.get('carryoverPPP')):
			session['carryoverPPP'] += "; " + request.form['catextppp']
		else:
			session['carryoverPPP'] = request.form['catextppp']

	if (request.form.get('catextppm')):
		if (session.get('carryoverPPM')):
			session['carryoverPPM'] += "; " + request.form['catextppm']
		else:
			session['carryoverPPM'] = request.form['catextppm']

	if (request.form.get('catextppmimg')):
		if (session.get('carryoverPPMImgs')):
			session['carryoverPPMImgs'] += "; " + request.form['catextppmimg']
		else:
			session['carryoverPPMImgs'] = request.form['catextppmimg']

	if (request.form.get('catextpinp')):
		if (session.get('carryoverPinP')):
			session['carryoverPinP'] += "; " + request.form['catextpinp']
		else:
			session['carryoverPinP'] = request.form['catextpinp']

	return redirect(request.referrer)

@app.route('/carryover-button') #Carryover button found on multiple pages
def carryover_button():
	if (request.args.get('catextppp')):
		strargs = request.args['catextppp'].replace("[", "").replace("]", "")
		if (session.get('carryoverPPPids')):
			session['carryoverPPPids'] += strargs.split(",")
		else:
			session['carryoverPPPids'] = strargs.split(",")
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPP WHERE id in (" + strargs + ") ;"
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

	return redirect(request.referrer)

@app.route('/cleardata') #Start over, redirects to home page
def clearData():
	session['carryoverPPP'] = ""
	session['carryoverPPM'] = ""
	session['carryoverPPMImgs'] = ""
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

	return render_template('index.html')

@app.route('/savedata') #Copy saved data to database - may change
def saveData():

	cur = mysql.connection.cursor()
	saveQuery = """INSERT INTO FinalData(ARC, Region, Insula, Property, Room, PPM, PPP, PPMImgs, PinP)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
		ON DUPLICATE KEY UPDATE
		Region = VALUES(Region),
		Insula = VALUES(Insula),
		Property = VALUES(Property),
		Room = VALUES(Room),
		PPM = VALUES(PPM),
		PPP = VALUES(PPP),
		PPMImgs = VALUES(PPMImgs),
		PinP = VALUES(PinP);"""

	queryvars = [session['arc']]
	if (session.get('region')):
		queryvars.append(session['region'])
	else:
		queryvars.append("")
	if (session.get('insula')):
		queryvars.append(session['insula'])
	else:
		queryvars.append("")
	if (session.get('property')):
		queryvars.append(session['property'])
	else:
		queryvars.append("")
	if (session.get('room')):
		queryvars.append(session['room'])
	else:
		queryvars.append("")


	if (session.get('carryoverPPP')):
		queryvars.append(session['carryoverPPP'])
	else:
		queryvars.append("")
	if (session.get('carryoverPPM')):
		queryvars.append(session['carryoverPPM'])
	else:
		queryvars.append("")
	if (session.get('carryoverPPMImgs')):
		queryvars.append(session['carryoverPPMImgs'])
	else:
		queryvars.append("")
	if (session.get('carryoverPinP')):
		queryvars.append(session['carryoverPinP'])
	else:
		queryvars.append("")


	cur.execute(saveQuery, queryvars)
	mysql.connection.commit()
	cur.close()

	return redirect(request.referrer)

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
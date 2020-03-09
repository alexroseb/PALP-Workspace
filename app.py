from flask import Flask, render_template, session, json, request, redirect
from flask_mysqldb import MySQL
from google.cloud import translate_v2 as translate
import google.auth
from google.oauth2 import service_account
import logging

app = Flask(__name__)
app.config["SECRET_KEY"] = "ShuJAxtrE8tO5ZT"

# MySQL configurations
app.config['MYSQL_USER'] = 'abrenon'
app.config['MYSQL_PASSWORD'] = 'anywheremysql'
app.config['MYSQL_DB'] = 'abrenon$workspace'
app.config['MYSQL_HOST'] = 'abrenon.mysql.pythonanywhere-services.com'
mysql = MySQL(app)

credentials = service_account.Credentials.from_service_account_file("/home/abrenon/My Project-1f2512d178cb.json")
translate_client = translate.Client(credentials=credentials)

romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]

@app.route("/")
def index():
	reg = ins = prop = room = arc = gdoc = ""

	if (session.get('region')):
		reg = session['region']
	if (session.get('insula')):
		ins = session['insula']
	if (session.get('property')):
		prop = session['property']
	if (session.get('room')):
		room = session['room']
	if (session.get('arc')):
		arc = session['arc']
	if (session.get('gdoc')):
		gdoc = session['gdoc']


	return render_template('index.html',
		region=reg, insula=ins, property=prop, room=room,
		gdoc=gdoc, arc=arc)

@app.route("/PPP")
def showPPP():

	pppCur = mysql.connection.cursor()
	pppQuery = "SELECT id, description FROM PPP WHERE location LIKE %s;"
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

	ppp = reg = ins = prop = room = iframeurl = ""

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
		catextppp=ppp, dbdata = dataplustrans, transdata = transdata, indices = indices,
		region=reg, insula=ins, property=prop, room=room, iframeurl = iframeurl)

@app.route('/PPM')
def showPPM():

	ppmCur = mysql.connection.cursor()
	ppmQuery = "SELECT id, description FROM PPM WHERE location LIKE %s;"
	loc = ""
	if (session.get('region')):
		romin = int(session['region']) - 1
		if romin >= 0 and romin < len(romans):
			romreg = romans[romin]
			loc += romreg
	if (session.get('insula')):
		loc += session['insula']
	if (session.get('property')):
		loc += session['property']
	if (session.get('room')):
		loc += session['room']

	if loc != "":
		loc += "%"

	ppmCur.execute(ppmQuery, [loc])
	data = ppmCur.fetchall()
	ppmCur.close()

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

	ppm = ppmimg = reg = ins = prop = room = iframeurl = ""

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
		catextppm=ppm, catextppmimg=ppmimg, dbdata = dataplustrans, transdata = transdata, indices = indices,
		region=reg, insula=ins, property=prop, room=room, iframeurl = iframeurl)

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


@app.route('/PinP')
def showPinP():
	pinp = reg = ins = prop = room = ""

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
		catextpinp=pinp, 
		region=reg, insula=ins, property=prop, room=room)

@app.route('/help')
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

@app.route('/GIS')
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


@app.route('/descriptions')
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

@app.route('/carryover', methods=['POST'])
def carryover_text():
	if (request.form.get('catextppp')):
		if (session.get('carryoverPPP')):
			session['carryoverPPP'] += "<br/>" + request.form['catextppp']
		else:
			session['carryoverPPP'] = request.form['catextppp']
		
	if (request.form.get('catextppm')):
		if (session.get('carryoverPPM')):
			session['carryoverPPM'] += "<br/>" + request.form['catextppm']
		else:
			session['carryoverPPM'] = request.form['catextppm']
		
	if (request.form.get('catextppmimg')):
		if (session.get('carryoverPPMImgs')):
			session['carryoverPPMImgs'] += "<br/>" + request.form['catextppmimg']
		else:
			session['carryoverPPMImgs'] = request.form['catextppmimg']
		
	if (request.form.get('catextpinp')):
		if (session.get('carryoverPinP')):
			session['carryoverPinP'] += "<br/>" + request.form['catextpinp']
		else:
			session['carryoverPinP'] = request.form['catextpinp']
		
	return redirect(request.referrer)

@app.route('/carryover-button')
def carryover_button():
	if (request.args.get('catextppp')):
		strargs = request.args['catextppp'].replace("[", "").replace("]", "")
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPP WHERE id in (" + strargs + ") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			if d[1] == 1:
				dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "<br/>"

		if (session.get('carryoverPPP')):
			session['carryoverPPP'] += "<br/>" + dataCopy
		else:
			session['carryoverPPP'] = dataCopy

	if (request.args.get('catextppm')):
		strargs = request.args['catextppm'].replace("[", "").replace("]", "")
		carryCur = mysql.connection.cursor()
		carryQuery = "SELECT description, reviewed FROM PPM WHERE id in (" + strargs + ") ;"
		carryCur.execute(carryQuery)
		dataList = carryCur.fetchall()
		carryCur.close()

		dataCopy = ""
		for d in dataList:
			if d[1] == 1:
				dataCopy += translate_client.translate(d[0], target_language="en", source_language="it")['translatedText'] + "<br/>"

		if (session.get('carryoverPPM')):
			session['carryoverPPM'] += "<br/>" + dataCopy
		else:
			session['carryoverPPM'] = dataCopy

	return redirect(request.referrer)

@app.route('/cleardata')
def clearData():
	session['carryoverPPP'] = ""
	session['carryoverPPM'] = ""
	session['carryoverPPMImgs'] = ""
	session['carryoverPinP'] = ""

	session['arc'] = ""
	session['region'] = ""
	session['insula'] = ""
	session['property'] = ""
	session['room'] = ""

	session['gdoc'] = ""

	return render_template('index.html')

@app.route('/savedata')
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

@app.route('/search', methods=['POST'])
def search():
	if (request.form.get('region')):
		session['region'] = request.form['region']
	if (request.form.get('insula')):
		session['insula'] = request.form['insula']
	if (request.form.get('property')):
		session['property'] = request.form['property']
	if (request.form.get('room')):
		session['room'] = request.form['room']
	return redirect(request.referrer)

@app.route('/init', methods=['POST'])
def init():
	session['arc'] = request.form['arc']
	session['gdoc'] = request.form['gdoc']
	if (request.form.get('region')):
		session['region'] = request.form['region']
	if (request.form.get('insula')):
		session['insula'] = request.form['insula']
	if (request.form.get('property')):
		session['property'] = request.form['property']
	if (request.form.get('room')):
		session['room'] = request.form['room']
	return redirect('/PPP')


if __name__ == "__main__":
	app.run()
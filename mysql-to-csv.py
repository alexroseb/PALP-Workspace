import pymysql
import csv

conn = pymysql.connect(host='abrenon.mysql.pythonanywhere-services.com', user='abrenon', password='anywheremysql', database='abrenon$workspace')
cursor = conn.cursor()
query = 'select * from FinalData'
cursor.execute(query)
with open("output.csv","w") as outfile:
    writer = csv.writer(outfile, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(col[0] for col in cursor.description)
    for row in cursor:
        writer.writerow(row)
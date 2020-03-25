# MYSQL Commands

## Create tables:

```mysql
CREATE TABLE IF NOT EXISTS FinalData (
	ARC VARCHAR(30) NOT NULL PRIMARY KEY,
	Region VARCHAR(10),
	Insula VARCHAR(10),
	Property VARCHAR(10),
	Room VARCHAR(10),
	PPM MEDIUMTEXT,
	PPP MEDIUMTEXT,
	PPMimgs MEDIUMTEXT,
	PinP MEDIUMTEXT
);
```
^^^^^ IF do again, use TEXT not MEDIUMTEXT

```mysql
CREATE TABLE IF NOT EXISTS PPP (
	id VARCHAR(30) NOT NULL PRIMARY KEY,
	location VARCHAR(30),
	description TEXT,
	reviewed BOOL
);

CREATE TABLE IF NOT EXISTS PPM (
	id VARCHAR(30) NOT NULL PRIMARY KEY,
	location VARCHAR(30),
	description TEXT,
	reviewed BOOL
);
```

## Loading from csvs

```mysql
LOAD DATA LOCAL INFILE '/home/abrenon/PPP-123short.csv' INTO TABLE PPP FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';
```
IMPORTANT: make sure it's set to Unix line endings

## Importing PinP:

```bash
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_webpages.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_webpage_images.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_box_images.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_azure_img_desc_x.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_addresses_x.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_azure_img_tags_x.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_image_hash.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_azure_img_desc.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace' < database_tables/webpage_images_tbl_addresses.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_azure_img_tags.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_addresses_box_x.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_addresses_box.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_azure_img_tags_box_x.sql
mysql -u abrenon -h abrenon.mysql.pythonanywhere-services.com 'abrenon$workspace'  < database_tables/webpage_images_tbl_azure_img_tags_box.sql
```

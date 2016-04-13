setup:
	sudo apt-get install python3.4 python3-pip python-virtualenv

venv_install:
	virtualenv --no-site-packages -p python3.4 venv
	bash -c "source venv/bin/activate && pip install -r requirements.txt"

_db_requirements_install:
	sudo apt-get install postgresql postgresql-contrib python-psycopg2
	# sudo -u postgres dropdb -e --if-exists xopay-processing
	# sudo -u postgres dropuser -e --if-exists xopay

_mac_db_requirements_install:
	brew install postgresql
	bash -c "source venv/bin/activate && \
		PATH=$(PATH):/Library/PostgreSQL/9.5/bin/ pip install psycopg2 &&\
		PATH=$(PATH):/Library/PostgreSQL/9.5/bin/ pip install Momoko"

_db_install:
	sudo -u postgres psql -c "CREATE USER xopayadmin WITH PASSWORD 'xopay';"
	sudo -u postgres psql -c "CREATE DATABASE xopayprocessing OWNER xopayadmin;"
	sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE xopayprocessing TO xopayadmin"
	sudo -u postgres psql xopayprocessing -c "CREATE TABLE transactions (ID SERIAL PRIMARY KEY, amount double precision NOT NULL, comission double precision, destination varchar(10000) NOT NULL, source varchar(10000) NOT NULL, description varchar(1000), status varchar(100) NOT NULL, currency varchar(3) NOT NULL, uuid varchar(50) NOT NULL, source_auth_response varchar(255), source_capture_response varchar(255), source_hold_id varchar(10), source_order_id varchar(10),  source_merchant_data varchar(255));"
	sudo -u postgres psql xopayprocessing -c "GRANT ALL PRIVILEGES ON TABLE transactions TO xopayadmin"
	sudo -u postgres psql xopayprocessing -c "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public to xopayadmin;"

mac_db_install: _mac_db_requirements_install _db_install

db_install: _db_requirements_install _db_install

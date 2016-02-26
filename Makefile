setup:
	sudo apt-get install python3.4 python3-pip python-virtualenv

venv_install:
	virtualenv --no-site-packages -p python3.4 xopay_venv
	bash -c "source xopay_venv/bin/activate && pip install -r requirements.txt"

postgresql_install:
    sudo apt-get install postgresql postgresql-contrib python-psycopg2
    sudo -u postgres dropdb -e --if-exists xopay
    sudo -u postgres dropuser -e --if-exists xopay
    sudo -u postgres psql -c "CREATE USER xopay WITH PASSWORD 'xopay'; CREATE DATABASE xopay OWNER xopay; GRANT ALL PRIVILEGES ON DATABASE xopay TO xopay"

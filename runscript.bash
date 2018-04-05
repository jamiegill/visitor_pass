python3 -m venv env
source env/bin/activate
sudo service postgresql start
python3 manage.py run &

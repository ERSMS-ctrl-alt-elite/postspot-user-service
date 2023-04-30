# ERSMS_beer_hangout_app
## Managing database
Initialize database
```
flask --app main.py db init
```
Create migrations
```
flask --app main.py db migrate
```
Apply migrations
```
flask --app main.py db upgrade
```
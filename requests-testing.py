from flask import Flask
import requests

DEBUG = True

app = Flask(__name__)
app.debug = DEBUG

payload = {
    'redirect_uri': '/',
    'response_type': 'code',
    'client_id': '524876334284.apps.googleusercontent.com'
}

r = requests.get('https://accounts.google.com/o/oauth2/auth', params=payload)
print r.json()

if __name__ == "__main__":
    app.run(debug=True)

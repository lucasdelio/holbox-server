from flask import Flask, request
import pymongo
from bson import json_util
import json
from datetime import datetime
from flask_cors import CORS, cross_origin
from cryptography.fernet import Fernet
from bson.objectid import ObjectId
import os

GOOGLE_USER_INFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
JSON_HEADER = {'content-type':'application/json'}
TTL_ = 24*60*60 #24 hs ttl for generated tokens
TOKEN_COOKIE_NAME = 'TOKEN_COOKIE_NAME'

app = Flask(__name__)
CORS(app)

key = os.environ['KEY'] #read the key from environment variable
ferne = Fernet(key)     #initialize fernet with the key

client = pymongo.MongoClient('mongodb://localhost:27017/')
articles_collection = client.holbox_database.articles_collection

@app.route('/articles')
def articles():
    p = articles_collection.find()
    return json_util.dumps(p), 200, JSON_HEADER
    
@app.route('/article', methods=['GET','PUT','DELETE'])
def article_by_id():
    id = request.args.get('id')
    if request.method == 'GET':
        if not id: return 'no id param',400
        print(id)
        a = articles_collection.find_one( {'_id': ObjectId(id)} )
        if not a :
            return '',204 #204 no content
        return json_util.dumps(a), 200, JSON_HEADER
    if request.method == 'PUT':
        try:
            body = request.data.decode('utf8')
            articles_collection.insert_one( {
                'markdown':body,
                'date': str(datetime.utcnow())
                })
            return '',200
        except:
            return 'Invalid body',400
    if request.method == 'DELETE':
        if not id: return 'no id param',400
        result = articles_collection.delete_one( {'_id': ObjectId(id)} )
        if result.deleted_count > 0:
            return '',200
        return '',204

if __name__ == '__main__':
    app.run(debug=True)
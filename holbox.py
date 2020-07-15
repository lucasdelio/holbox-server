from flask import Flask, request
import pymongo
from bson import json_util
import json
from datetime import datetime
from flask_cors import CORS, cross_origin
from cryptography.fernet import Fernet
from bson.objectid import ObjectId
import os

MARKDOWN = "markdown"
TITLE = "title"
CATEGORY = "category"
TAGS = "tags"

GOOGLE_USER_INFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
JSON_HEADER = {'content-type':'application/json'}
TTL_ = 24*60*60 #24 hs ttl for generated tokens
TOKEN_COOKIE_NAME = 'TOKEN_COOKIE_NAME'

app = Flask(__name__)
CORS(app)

#key = os.environ['KEY'] #read the key from environment variable
#ferne = Fernet(key)     #initialize fernet with the key

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['holbox_database']
articles_collection = db['articles_collection']

ARTICLES_PROJECTION = {'_id': 1, 'thumbnail':1, 'date':1, 'title':1, 'category':1 }


@app.route('/articles')
def articles():
    category = request.args.get('category')
    if category:
        p = articles_collection.find({"category": category}, ARTICLES_PROJECTION)
    else:
        p = articles_collection.find({}, ARTICLES_PROJECTION)
    return json_util.dumps(p), 200, JSON_HEADER


def isValidArticle(a):
    return a[MARKDOWN] and a[TITLE] and a[CATEGORY] and a[TAGS]


@app.route('/article', methods=['GET','POST','DELETE','PUT'])
def article_by_id():
    id = request.args.get('id')
    if request.method == 'GET':   
        if not id: return 'no id param', 400
        a = articles_collection.find_one( {'_id': ObjectId(id)} )
        if not a :
            return '', 400
        return json_util.dumps(a), 200, JSON_HEADER
    if request.method == 'POST':
        try:
            article = json.loads( request.data.decode('utf8')  )
            if not isValidArticle(article):
                return 'invalid article format', 400
            article['date'] = str(datetime.utcnow())
            articles_collection.insert_one( article )
            return '', 200
        except:
            return 'Invalid body, body must be a valid article', 400
    if request.method == 'DELETE':
        if not id: return 'no id param', 400
        result = articles_collection.delete_one( {'_id': ObjectId(id)} )
        if result.deleted_count > 0:
            return '', 200
        return 'id not found', 400
    if request.method == 'PUT':   
        if not id:
            return 'no id param', 400
        article = json.loads( request.data.decode('utf8')  )
        if not isValidArticle(article):
            return 'invalid article format', 400
        a = articles_collection.find_one( {'_id': ObjectId(id)} )
        if not a:
            return 'id not found', 400
        article["date"] = a["date"] #preserve the old date
        articles_collection.replace_one( {'_id': ObjectId(id)} , article)
        return article, 200, JSON_HEADER


@app.route('/reload_from_mock',methods=['POST'])
def clear_all_articles():
    db.drop_collection(articles_collection)
    with open('mocked_articles.json', encoding='utf-8') as json_file:
        articles = json.load(json_file)
        articles_collection.insert_many(articles)
    return '', 200


if __name__ == '__main__':
    app.run(debug=True)
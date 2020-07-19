from flask import Flask, request
import pymongo
from bson import json_util
import json
from datetime import datetime
from flask_cors import CORS, cross_origin
from cryptography.fernet import Fernet
from bson.objectid import ObjectId
import os
import unidecode

MARKDOWN = 'markdown'
TITLE = 'title'
CATEGORY = 'category'
TAGS = 'tags'
THUMBNAIL = 'thumbnail'
DATE = 'date'
ID = 'id'
PAGE = 'page'

GOOGLE_USER_INFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
JSON_HEADER = {'content-type':'application/json'}
TTL_ = 24*60*60 #24 hs ttl for generated tokens
TOKEN_COOKIE_NAME = 'TOKEN_COOKIE_NAME'
PAGE_SIZE = 'page_size'
PAGE_SIZE_DEFAULT = 10

app = Flask(__name__)
CORS(app)

#key = os.environ['KEY'] #read the key from environment variable
#ferne = Fernet(key)     #initialize fernet with the key

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['holbox_database']
articles_collection = db['articles_collection']
articles_collection.create_index([(ID, pymongo.ASCENDING)], unique=True)

ARTICLES_PROJECTION = {'_id': 0, ID:1, THUMBNAIL:1, DATE:1, TITLE:1, CATEGORY:1 }
SINGLE_ARTICLE_PROJECTION = {'_id': 0, ID:1, THUMBNAIL:1, DATE:1, TITLE:1, CATEGORY:1,MARKDOWN:1 }


@app.route('/articles')
def articles():
    category = request.args.get(CATEGORY)
    page = int(request.args.get(PAGE) or 0)
    page_size = int(request.args.get(PAGE_SIZE) or PAGE_SIZE_DEFAULT)
    if category:
        p = articles_collection.find({CATEGORY: category}, ARTICLES_PROJECTION)
    else:
        p = articles_collection.find({}, ARTICLES_PROJECTION)
    p = p.sort(DATE, -1) #reverse the array
    p = p[ (page)*page_size : (page+1)*page_size ] #pagination
    return json_util.dumps(p), 200, JSON_HEADER


def isValidArticle(a): #check the required attributes
    return {MARKDOWN, TITLE, CATEGORY, THUMBNAIL} <= a.keys()

def convertTitleToId(s):
    s = unidecode.unidecode(s) #remove accents
    s = s.lower()
    s = s.replace(" ","-")
    s = s.replace(".","") #remove the dots
    return s

@app.route('/article', methods=['GET','POST','DELETE','PUT'])
def article_by_id():
    id = request.args.get(ID)
    if request.method == 'GET':   
        if not id: return 'no id param', 400
        a = articles_collection.find_one( {ID: id}, SINGLE_ARTICLE_PROJECTION )
        if not a :
            return '', 400
        return json_util.dumps(a), 200, JSON_HEADER
    if request.method == 'POST': #create a new article, passed in body
        try:
            article = json.loads( request.data.decode('utf8')  )
            if not isValidArticle(article):
                return 'invalid article format, missing some key', 400
            article[DATE] = str(datetime.utcnow())
            article[ID] = convertTitleToId(article[TITLE])
            articles_collection.insert_one( article )
            return '', 200
        except:
            return 'Invalid body, body must be a valid article', 400
    if request.method == 'DELETE':
        if not id: return 'no id param', 400
        result = articles_collection.delete_one( {ID: id} )
        if result.deleted_count > 0:
            return '', 200
        return 'id not found', 400
    if request.method == 'PUT':   
        if not id:
            return 'no id param', 400
        article = json.loads( request.data.decode('utf8')  )
        if not isValidArticle(article):
            return 'invalid article format, missing some key', 400
        a = articles_collection.find_one( {ID: id}, SINGLE_ARTICLE_PROJECTION )
        if not a:
            return 'id not found', 400
        article[DATE] = a[DATE] #preserve the old date
        article[ID] = article[TITLE].replace(" ","_")
        articles_collection.replace_one( {ID: id} , article)
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
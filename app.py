## entrypoint for Bestbowl API

import os
import dotenv
dotenv.load_dotenv()
import card_adder
import datetime
import secrets
import base64
import jsonpickle
from fsrs import FSRS, Card, SchedulingInfo, ReviewLog ## this line will probably throw an error because i had to modify fsrs's __init__.py to give me the classes i need. this library is kinda dumb.
import carder
import flask
import json
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, redirect as r, Response
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
# Enter a secret key
app.config["SECRET_KEY"] = "ENTER YOUR SECRET KEY"
# Initialize flask-sqlalchemy extension
db = SQLAlchemy()
INITIAL_SETTING = 1 ## hard


dotenv.load_dotenv()
app.secret_key = os.environ['SECRET_FLASK_KEY'].encode("ascii")
F = FSRS()

    


# Create user model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(), nullable=False)
    data = db.Column(db.String(), nullable=True)

def stringify(obj):
    return json.dumps(obj)
def get_default_user_data():
    '''
    versioning:
    1.0.0: uses jsonpickle to turn the ScheduleInfo class into json and back. not a good solution but it works
    '''
    return {
        "storage_version": "1.0.0",
        "max_new_cards": 3,
        "last_added_cards": "0000-00-00",
        "cards": [] ##this will be a large array of (uuid, (int, schedulingstuff))
    }

def serialize(s: any):
    '''
    serialize arbritary class into json object (depth not max)
    '''
    data = {}
    for property in s.__dict__:
        cardobj = s.__dict__[property].__dict__.copy()
        for entry in cardobj:
            if type(cardobj[entry]) == datetime.datetime:
                cardobj[entry] = cardobj[entry].isoformat()
        data[property] = cardobj
    return data
def serialize_card(s: [str, SchedulingInfo]):
    '''
    turn a scheduling info into a json_readable object.
    '''
    data = {}
    s2 = s[1]
    for property in s2.__dict__:
        
        cardobj = s2.__dict__[property].__dict__.copy()
        for entry in cardobj:
            if type(cardobj[entry]) == datetime.datetime:
                cardobj[entry] = cardobj[entry].isoformat()
        data[property] = cardobj
    questionurl = request.host_url + "uuid_to_question?card_uuid="+s[0]
    data["url_to_question"] = questionurl
    return data
def get_random_user_id():
    return secrets.token_hex()
# Initialize app with extension
db.init_app(app)

with app.app_context():
    db.create_all()
# As of November 2023, WCS clusters are not yet compatible with the new API introduced in the v4 Python client.
# Accordingly, we show you how to connect to a local instance of Weaviate.
# Here, authentication is switched off, which is why you do not need to provide the Weaviate API key.
def needs_params(words, optional=None):
   
    def inner(func): ## my brain is hurting from the triple decorator
        @wraps(func)
        def moreInner(**kwargs):
            validArgs = request.args.copy()
            if id in validArgs:
                del validArgs['id']
            
            newkwargs = {}
            for i, word in enumerate(words):
                if not request.args.get(word):
                    if (not (optional is None)) and (optional[i] == True): ##this wouldnt work in a compiled language 😂
                        return "Error: Missing param argument '" + word + "'"
                    newkwargs[word] = None
                else:
                    newkwargs[word] = request.args.get(word)
            
            newkwargs = {**newkwargs, **kwargs}
            return func(**newkwargs)
        return moreInner
    return inner

def needs_user_id(func):
    @wraps(func)
    def moreInner(**kwargs):
        user = None
        if (request.args.get("id")):
            user = User.query.filter_by(user_id=request.args.get("id")).first()
            if user is None:
                raise IndexError("User is not valid")
        else:
            raise KeyError("Please provide a valid user id")
        return func(**kwargs, user=user)
    return moreInner



def get_date(): 
    ## gets time mm/dd/yy
    return datetime.date.today().strftime("%Y-%m-%d")

def get_user_cards(user):
    userinfo = json.loads(user.data)
    return [[a[0], save_deserialize_schedule(a[1])] for a in userinfo['cards']]
def put_back_user_cards(user, cards):
    serialized_cards = [[a[0], save_serialize_schedule(a[1])] for a in cards]
    userinfo = json.loads(user.data)
    userinfo['cards'] = serialized_cards
    user.data = json.dumps(userinfo)
    db.session.commit()
    
def save_serialize_schedule(card: SchedulingInfo):
    return json.loads(jsonpickle.encode(card, unpicklable=True))       

def save_deserialize_schedule(card: dict):
    return jsonpickle.decode(json.dumps(card), classes=(SchedulingInfo, Card, ReviewLog)) ##efficency at it's finest
    
def get_user_card_by_uuid(user: User, card_uuid: str, cards=None) -> [str, SchedulingInfo]:
    if (cards == None):
        all_cards = get_user_cards(user)
    else:
        all_cards = cards
    _cards = list(filter(lambda c: c[0] == card_uuid, all_cards))
    if len(_cards) == 0:
        raise ValueError("Card UUID is either not in user's deck or not a valid UUID.")
    return _cards[0]

def get_due_date_from_sched(sched: SchedulingInfo):
    return sched.card.due


def add_card(card: Card, userdata: dict):
    '''
    adds a card to the srs database
    '''
 
    uuid = str(card["metadata"]["uuid"])
    ## check if it exists
    new_fsrs_card = Card()
    scheduled_stuff = F.repeat(new_fsrs_card, datetime.datetime.now())
    same_cards = list(filter(lambda x: x[0] == uuid, userdata['cards']))
    if len(same_cards) > 0:
        raise KeyError("Card already present in DB")
    card = scheduled_stuff[INITIAL_SETTING]
    # srs_card = card
    userdata['cards'].append((uuid, save_serialize_schedule(card)))
    return card
   


def updateUserData(user: User):
    '''
    Computes user's SRS data and such.
    '''
    
    userdata = json.loads(user.data)
    # print(userdata)
    if userdata['last_added_cards'] != get_date():
        for _ in range(userdata['max_new_cards']):
            new_card = carder.get_random_card()
            add_card(new_card, userdata)
        userdata['last_added_cards'] = get_date()
    # print(userdata)
    user.data = json.dumps(userdata)
    db.session.commit()
    
@app.route("/")
def version():
    message = """
    <code>
    BestBowl API <br>
    
    {version_info} <br>
    
    Please don't use this API! <br>
    The code is all on github! <br>
    Thank you!! <br>
    </code>
    """
    with os.popen("git log") as f:
        version_info = f.read()
    return message.format(version_info=version_info)


@app.route("/search_cards")
@needs_params(["query", "limit", "subcategories"])
def search_cards(query=None, limit=None, user=None, subcategories=None):
    if (subcategories != None):
        subcategories = json.loads(subcategories)
    results = carder.get_near_card(query, limit, subcategories=subcategories)
    return results

@app.route("/practice_card")
@needs_user_id
@needs_params(["rating", "card_uuid"])
def practice_card(rating=None, card_uuid=None, user=None):
        rating = int(rating)
        if (rating not in range(1, 5)):
            raise ValueError("Rating must be integer in range [1,4], inclusive")
        
        all_cards = get_user_cards(user)
        card = get_user_card_by_uuid(user, card_uuid, cards=all_cards)
        scheduling_info: SchedulingInfo = card[1]
        scheduling_perms = F.repeat(scheduling_info.card, datetime.datetime.now())
        card[1].card = scheduling_perms[rating].card
        # print(all_cards[0q][1].card.__dict__)
        put_back_user_cards(user, all_cards)
        return Response("done", status=201)

@app.route("/view_cards") 
@needs_user_id
@needs_params(["due"], optional=[True])
def view_due_cards(user=None, due=None):
    all_cards = get_user_cards(user)
    if due == "true":
        # dates = map(get_due_date_from_sched, all_cards)
        due_dates = list(map(serialize_card,filter(lambda sched: sched[1].card.due <= datetime.datetime.now(), all_cards)))
        return due_dates
    return list(map(serialize_card, all_cards))


@app.route("/get_random_question")
@needs_user_id
def get_random_question(user=None):
    '''
    gets a random new card from weaviate and adds it to the user's deck, and returns the question.
    '''
    userdata = json.loads(user.data)
    weaviate_card = carder.get_random_card()
    srs_card = add_card(weaviate_card, userdata)
    card = {**weaviate_card, "srs": serialize(srs_card)}
    return card


@app.route("/uuid_to_question")
@needs_user_id
@needs_params(["card_uuid"])
def uuid_to_question(card_uuid=None, user=None):
    question = carder.get_card_by_uuid(card_uuid)
    srs_card = get_user_card_by_uuid(user, card_uuid)
    card = {**question, "srs": serialize(srs_card)}
    return card
        
@app.route("/create_user")
@needs_params(["redirect"], optional=[True])
def create_user(redirect=None):
    ### if someone doesnt have a user id, this makes them a new user
    new_user = User(user_id=get_random_user_id(), data=stringify(get_default_user_data()))
    db.session.add(new_user)
    db.session.commit()
    if (redirect == 'true'):
        return r("/get_user_data?id="+new_user.user_id)
    # print(new_user.uswer_id)
    return new_user.user_id

@app.route("/get_user_data")
@needs_user_id
def get_user_data(user=None):
        
    updateUserData(user)
    return user.data
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)
   
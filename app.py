## entrypoint for Bestbowl API

import os
import dotenv
dotenv.load_dotenv()
import card_adder
import datetime
import secrets
import jsonpickle
from fsrs import FSRS, Card, SchedulingInfo, ReviewLog ## this line will probably throw an error because i had to modify fsrs's __init__.py to give me the classes i need. this library is kinda dumb.
import carder
import flask
import json
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, redirect as r
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
# Enter a secret key
app.config["SECRET_KEY"] = "ENTER YOUR SECRET KEY"
# Initialize flask-sqlalchemy extension
db = SQLAlchemy()
 


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
    return {
        "max_new_cards": 3,
        "last_added_cards": "0000-00-00",
        "cards": [] ##this will be a large array of (uuid, (int, schedulingstuff))
    }
def get_random_user_id():
    return secrets.token_hex()
# Initialize app with extension
db.init_app(app)

with app.app_context():
    db.create_all()
# As of November 2023, WCS clusters are not yet compatible with the new API introduced in the v4 Python client.
# Accordingly, we show you how to connect to a local instance of Weaviate.
# Here, authentication is switched off, which is why you do not need to provide the Weaviate API key.
def needs_params(words, optional=False):
    def inner(func): ## my brain is hurting from the triple decorator
        @wraps(func)
        def moreInner(**kwargs):
            validArgs = request.args.copy()
            if id in validArgs:
                del validArgs['id']
            
            newkwargs = {}
            for word in words:
                if not request.args.get(word):
                    if not optional:
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
    
def serialize_schedule(scheduling_stuff: dict[int, SchedulingInfo]):
    ## arghhh i gotta do this manually
    sched_info = scheduling_stuff.values()
    data = {}
    for index, sched in enumerate(sched_info):
        card = sched.card
        review_log = sched.review_log
        ##first card
        card_dict = card.__dict__
        card_dict['due'] = datetime.datetime.isoformat(card_dict['due'])
        card_dict['last_review'] = datetime.datetime.isoformat(card_dict['last_review'])
        ##second review
        review_dict = review_log.__dict__
        review_dict['review'] = datetime.datetime.isoformat(review_dict['review'])
        card_info = [card_dict, review_dict]
        data[index+1] = card_info
    return data

def deserialize_schedule(json_stuff: dict[int, dict]):
    
    data = {}
    for index, sched in enumerate(json_stuff.values()):
        card_dict = sched[0]
        # print(card_dict)
        card_dict['due'] = datetime.datetime.fromisoformat(card_dict['due'])
        card_dict['last_review'] = datetime.datetime.fromisoformat(card_dict['last_review'])
        review_dict = sched[1]
        review_dict['review'] = datetime.datetime.fromisoformat(review_dict['review'])
        # print(review_dict)
        new_card = Card() 
        ## first card
        for key in card_dict:
            setattr(new_card, key, card_dict[key])
        review_log = ReviewLog(*review_dict) ## ORDER MATTERS
        sched_info = SchedulingInfo(new_card, review_log)
        
        # print(sched_info)
        # print(review_log)
        # print(new_card)
        data[index+1] = sched_info ## zero is there for equality purposes
    return data
    

def updateUserData(user: User):
    '''
    Computes user's SRS data and such.
    '''
    
    userdata = json.loads(user.data)
    # print(userdata)
    if userdata['last_added_cards'] != get_date():
        for _ in range(userdata['max_new_cards']):
            new_card = carder.get_random_card()
            uuid = str(new_card.metadata.uuid)
            ## check if it exists
            new_fsrs_card = Card()
            scheduled_stuff = F.repeat(new_fsrs_card, datetime.datetime.now())
            same_cards = list(filter(lambda x: x[0] == uuid, userdata['cards']))
            if len(same_cards) > 0:
                continue
            userdata['cards'].append((uuid, serialize_schedule(scheduled_stuff)))
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


@app.route("/get_near_cards")
# @needs_user_id()
@needs_params(["word", "limit"])
def get_near_cards(word, limit, user=None):
    results = carder.get_near_cards(word, limit)
    return results

@app.route("/card_repetition")
@needs_user_id
@needs_params(["rating", "card_uuid"])
def card_repetition(rating, card_uuid, user=None):
        rating = int(rating)
        userinfo = json.loads(user.data)
        all_cards = [[a[0], deserialize_schedule(a[1])] for a in userinfo['cards']]
        card = list(filter(lambda c: c[0] == card_uuid, all_cards))[0]
        print("found card: " + repr(card)) 
        if (rating not in range(1, 4)):
            raise ValueError("Rating must be integer in range [1,4], inclusive")
        
        
@app.route("/create_user")
@optional_params(["redirect"])
def create_user(redirect):
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
   
from flask import Flask, request, jsonify, redirect
import json
import boto3
from flask import jsonify
from flask_awscognito import AWSCognitoAuthentication
from flask_cors import CORS
from bson.json_util import dumps
import pymongo
from helpers import init_seq, get_next_sequence_value
from datetime import datetime
import watchtower, logging
import os
app = Flask(__name__)
CORS(app)

app.config['AWS_DEFAULT_REGION'] = os.environ['AWS_DEFAULT_REGION']
app.config['AWS_COGNITO_DOMAIN'] = os.environ['AWS_COGNITO_DOMAIN']
app.config['AWS_COGNITO_USER_POOL_ID'] = os.environ['AWS_COGNITO_USER_POOL_ID']
app.config['AWS_COGNITO_USER_POOL_CLIENT_ID'] = os.environ['AWS_COGNITO_USER_POOL_CLIENT_ID']
app.config['AWS_COGNITO_USER_POOL_CLIENT_SECRET'] = None
app.config['AWS_COGNITO_REDIRECT_URL'] = os.environ['AWS_COGNITO_REDIRECT_URL']
CONNECTION_STRING = os.environ['CONNECTION_STRING']

aws_auth = AWSCognitoAuthentication(app)

# sqs bootstrap
sqs = boto3.resource('sqs', region_name='eu-west-1')
queue = sqs.get_queue_by_name(QueueName='EpidemicSimulatorTasks')

# mongodb bootstrap
mongo = pymongo.MongoClient(CONNECTION_STRING)
db = mongo.get_database('simulationdb')
users = db.get_collection('users')
sims = db.get_collection('simulations')
counters = db.get_collection('counters')

logging.basicConfig(level=logging.INFO)
handler = watchtower.CloudWatchLogHandler()
app.logger.addHandler(handler)
logging.getLogger("werkzeug").addHandler(handler)

# @app.route('/log')
# def log():
#     app.logger.info("Amazing! :)")
#     return 'logged! :)'

@app.route('/')
def hello_world():
    return 'Hello World! This is epidemic simulator backend  :)'

# @app.route('/init')
# def init_db():
#     # init_seq(counters, 'user_id')
#     init_seq(counters, 'simulation_id')
#     return dumps(db.get_collection('counters').find())

# @app.route('/db')
# def test_db():
#     users.insert_one({'_id':get_next_sequence_value(counters, 'user_id') , 'name': 'Julio', 'age':'26', 'address': 'Peru'})
#     return dumps(users.find())

@app.route('/buy-orders', methods=["POST"])
@aws_auth.authentication_required
def buy_orders():
    data = request.json
    u = users.find_and_modify(query={"email": aws_auth.claims['email']},
                              update={"$inc": {"quota": int(data['num'])}})
    if u is None:
        return jsonify('ERROR: you are not authorized to run this command!'), 403
    else:
        return jsonify('Congratulations! You have loaded your account with '+str(data['num'])+' new orders!')

@app.route('/get-dashboard', methods=["GET"])
@aws_auth.authentication_required
def get_dashboard():
    #
    u = users.find_one({'email': aws_auth.claims['email']})
    quota = -1 if u is None else u['quota']
    enqueued = sims.find({'user_id': aws_auth.claims['email'], 'status':'ENQUEUED'}, ['order_time'])
    ready = sims.find({'user_id': aws_auth.claims['email'], 'status':'READY'}, ['order_time'])
    enqueued_list =  [] if enqueued is None else list(enqueued)
    ready_list = [] if ready is None else list(ready)
    response = {
        'quota': quota,
        'enqueued_count': len(enqueued_list),
        'enqueued_list': enqueued_list,
        'ready_count': len(ready_list),
        'ready_list': ready_list
    }
    app.logger.info("DASHBOARD_VISIT: by user "+aws_auth.claims['email'])
    return jsonify(response)

@app.route('/get-simulation', methods=["GET"])
@aws_auth.authentication_required
def get_simulation():
    sim_id = request.args['id']
    #
    s = sims.find_one({'_id': int(sim_id), 'user_id': aws_auth.claims['email']})
    # check if the simulation belongs to the current user
    if s is None:
        app.logger.warning("UNAUTHORIZED_SIMULATION_VIEW: by user " + aws_auth.claims['email'])
        return jsonify('YOU DO NOT HAVE PERMISSION TO ACCESS THIS SIMULATION!'), 403
    else:
        app.logger.info("SIMULATION_VIEW: by user " + aws_auth.claims['email'])
        return jsonify(s)

@app.route('/register-user', methods=["POST"])
@aws_auth.authentication_required
def register():
    claims = aws_auth.claims
    json_claims = jsonify({'claims': claims})
    data = json_claims["claims"]
    print(data)
    u = users.findOne({"email":data['email']})
    if u is None:
        app.logger.warning("DUPLICATE_EMAIL_REGISTRATION: for email " + data['email'])
        return jsonify('This username is already registered!')
    su=users.insert_one({
        '_id': get_next_sequence_value(counters, 'user_id'),
        'first_name': data['given_name'],
        'last_name': data['family_name'],
        'email': data['email'],
        'quota': 20,
        'billig_address': data['address']['formatted']
     })
    app.logger.info("NEW_USER_REGISRERED: with email " + data['email'])
    return jsonify(su)

@app.route('/user-data', methods=["GET"])
@aws_auth.authentication_required
def login():
    claims = aws_auth.claims
    print(jsonify({'claims': claims}))
    return jsonify({'claims': claims})

@app.route('/order-simulation', methods=["POST"])
@aws_auth.authentication_required
def enqueue():
    data = request.json
    u = users.find_and_modify(query={"email": aws_auth.claims['email'], "quota":{"$gt":0}}, update={"$inc":{"quota": -1}})
    if u is None:
        app.logger.warning("ORDER_WITH_INSUFFICIENT_QUOTA: by user " + aws_auth.claims['email'])
        return jsonify("ERROR: you have no orders left! Buy new orders to run this command.."), 403
    else:
        s=sims.insert_one({
            '_id':get_next_sequence_value(counters, 'simulation_id'),
            'order_time': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'parameters': data,
            'status': 'ENQUEUED',
            'user_id': aws_auth.claims['email']
        })
        # return jsonify(data)
        # Send message to SQS queue
        if s is not None:
            response = queue.send_message(
                # QueueUrl=queue_url,
                DelaySeconds=10,
                MessageBody=dumps(data),
                MessageAttributes={
                    'user_id': {
                        'DataType': 'String',
                        'StringValue': aws_auth.claims['email']
                    },
                    'simulation_id': {
                        'DataType': 'String',
                        'StringValue': str(s.inserted_id)
                    },
                },
            )
            app.logger.info("NEW_SIMULATION_ORDER: by user " + aws_auth.claims['email'])
            return jsonify(response['MessageId'])
        else:
            return jsonify('ERROR: Could not store the simulation order in the database'), 400

if __name__ == '__main__':
    app.run(debug=True)

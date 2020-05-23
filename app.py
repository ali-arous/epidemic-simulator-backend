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
app = Flask(__name__)
CORS(app)
import watchtower, logging
import os
app.config['AWS_DEFAULT_REGION'] = 'eu-west-1'
app.config['AWS_COGNITO_DOMAIN'] = 'https://epidemic-simulator-login.auth.eu-west-1.amazoncognito.com'
app.config['AWS_COGNITO_USER_POOL_ID'] = 'eu-west-1_nb1h2zCRl'
app.config['AWS_COGNITO_USER_POOL_CLIENT_ID'] = '20ts7p2m5aui7furnu89a0fkid'
app.config['AWS_COGNITO_USER_POOL_CLIENT_SECRET'] = None
app.config['AWS_COGNITO_REDIRECT_URL'] = "https://master.d2b045thd43tkr.amplifyapp.com/"
CONNECTION_STRING = "mongodb+srv://ali:Angel123@cluster0-b5ry8.mongodb.net/test?retryWrites=true&w=majority"
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
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
logging.getLogger().addHandler(handler)

@app.route('/log')
def log():

    app.logger.info("backend: Go for logging!")

    return 'logged! :)'

@app.route('/')
def hello_world():
    return 'Hello World! This is epidemic simulator backend  :)'

# @app.route('/init')
# def init_db():
#     # init_seq(counters, 'user_id')
#     init_seq(counters, 'simulation_id')
#     return dumps(db.get_collection('counters').find())

@app.route('/db')
def test_db():
    users.insert_one({'_id':get_next_sequence_value(counters, 'user_id') , 'name': 'Julio', 'age':'26', 'address': 'Peru'})
    return dumps(users.find())

@app.route('/get-dashboard', methods=["GET", "POST"])
@aws_auth.authentication_required
def get_dashboard():
    #
    enqueued = sims.find({'user_id': aws_auth.claims['email'], 'status':'ENQUEUED'}, ['order_time'])
    ready = sims.find({'status':'READY'}, ['order_time'])
    enqueued_list =  [] if enqueued is None else list(enqueued)
    ready_list = [] if ready is None else list(ready)
    response = {
        'enqueued_count': len(enqueued_list),
        'enqueued_list': enqueued_list,
        'ready_count': len(ready_list),
        'ready_list': ready_list
    }
    return jsonify(response)

@app.route('/get-simulation', methods=["GET", "POST"])
@aws_auth.authentication_required
def get_simulation():
    sim_id = request.args['id']
    #
    s = sims.find_one({'_id': int(sim_id), 'user_id': aws_auth.claims['email']})
    # check if the simulation belongs to the current user
    if s is None:
        return jsonify('YOU DO NOT HAVE PERMISSION TO ACCESS THIS SIMULATION!')
    else:
        return jsonify(s)

@app.route('/register-user', methods=["POST"])
def register():
    data = request.json
    u = users.findOne({"email":data['email']})
    if u is None:
        return jsonify('This username is already registered!')
    su=users.insert_one({
        '_id': get_next_sequence_value(counters, 'user_id'),
        'first_name': data['firstq_name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'quota': 20,
        'billig_address': data['billing_address']
     })
    return jsonify(su)

@app.route('/user-data', methods=["GET","POST"])
@aws_auth.authentication_required
def login():
    claims = aws_auth.claims
    print(jsonify({'claims': claims}))
    return jsonify({'claims': claims})

@app.route('/order-simulation', methods=["POST"])
@aws_auth.authentication_required
def enqueue():
    data = request.json
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
        return jsonify(response['MessageId'])
    else:
        return jsonify('ERROR: Could not store the simulation order in the database')

if __name__ == '__main__':
    app.run(debug=True)

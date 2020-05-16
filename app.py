from flask import Flask, request, jsonify, redirect
import json
import boto3
from flask_awscognito import AWSCognitoAuthentication
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['AWS_DEFAULT_REGION'] = 'eu-west-1'
app.config['AWS_COGNITO_DOMAIN'] = 'https://epidemic-simulator-login.auth.eu-west-1.amazoncognito.com'
app.config['AWS_COGNITO_USER_POOL_ID'] = 'eu-west-1_nb1h2zCRl'
app.config['AWS_COGNITO_USER_POOL_CLIENT_ID'] = '20ts7p2m5aui7furnu89a0fkid'
app.config['AWS_COGNITO_USER_POOL_CLIENT_SECRET'] = None
app.config['AWS_COGNITO_REDIRECT_URL'] = "https://master.d2b045thd43tkr.amplifyapp.com/"

aws_auth = AWSCognitoAuthentication(app)

@app.route('/')
def hello_world():
    return 'Hello World! This is epidemic simulator backend  :)'

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
    sqs = boto3.resource('sqs', region_name='eu-west-1'
                       # ,
                       # aws_access_key_id='AKIAZZ3N3RKYQHRRADPM',
                       # aws_secret_access_key='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',
                       )
    #arn:aws:sqs:eu-west-1:674003389105:EpidemicSimulatorTasks
    queue = sqs.get_queue_by_name(QueueName='EpidemicSimulatorTasks')
    # queue_url = 'https://sqs.eu-west-1.amazonaws.com/674003389105/EpidemicSimulatorTasks'

    # Send message to SQS queue
    response = queue.send_message(
        # QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'population': {
                'DataType': 'String',
                'StringValue': str(data['population'])
            },
            'numitartions': {
                'DataType': 'Number',
                'StringValue': str(data['numitartions'])
            },
            'latitude_1': {
                'DataType': 'Number',
                'StringValue': str(data['latitude_1'])
            },
            'longitude_1': {
                'DataType': 'Number',
                'StringValue': str(data['longitude_1'])
            },
            'latitude_2': {
                'DataType': 'Number',
                'StringValue': str(data['latitude_2'])
            },
            'longitude_2': {
                'DataType': 'String',
                'StringValue': str(data['longitude_2'])
            },
            'per_ini_infection': {
                'DataType': 'Number',
                'StringValue': str(data['per_ini_infection'])
            },
            'incubation_days': {
                'DataType': 'Number',
                'StringValue': str(data['incubation_days'])
            },
            'infection_days': {
                'DataType': 'Number',
                'StringValue': str(data['infection_days'])
            },
            'prob_infection': {
                'DataType': 'Number',
                'StringValue': str(data['prob_infection'])
            },
            'prob_immunity': {
                'DataType': 'String',
                'StringValue': str(data['prob_immunity'])
            },
            'aware_days': {
                'DataType': 'Number',
                'StringValue': str(data['aware_days'])
            },
            'prob_awareness': {
                'DataType': 'Number',
                'StringValue': str(data['prob_awareness'])
            },
            'prob_death': {
                'DataType': 'Number',
                'StringValue': str(data['prob_death'])
            },
            'lockdown_start': {
                'DataType': 'Number',
                'StringValue': str(data['lockdown_start'])
            },
            'lockdown_duration': {
                'DataType': 'Number',
                'StringValue': str(data['lockdown_duration'])
            },
            'prob_warningmsg': {
                'DataType': 'Number',
                'StringValue': str(data['prob_warningmsg'])
            },
            'prob_stayinghome': {
                'DataType': 'Number',
                'StringValue': str(data['prob_stayinghome'])
            },
            'schoolsper1000': {
                'DataType': 'String',
                'StringValue': str(data['schoolsper1000'])
            },
            'universitiesper1000': {
                'DataType': 'Number',
                'StringValue': str(data['universitiesper1000'])
            },
            'officesper1000': {
                'DataType': 'Number',
                'StringValue': str(data['officesper1000'])
            },
            'recreationsper1000': {
                'DataType': 'Number',
                'StringValue': str(data['recreationsper1000'])
            }
        },
        MessageBody=(
            'New Simulation Order'
        )
    )

    return response['MessageId']

if __name__ == '__main__':
    app.run(debug=True)

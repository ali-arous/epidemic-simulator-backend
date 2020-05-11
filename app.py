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

@app.route('/.well-known/acme-challenge/KVd03v30OcnxabFx04YTQF9JHAyzMcHFX_h8qcd74Z8')
def challenge():
    return 'KVd03v30OcnxabFx04YTQF9JHAyzMcHFX_h8qcd74Z8.5fkaMOCD9vm1P8tFXSwxybkcGsXNQIkG5z2uB9mZz_0'

@app.route('/order-simulation', methods=["POST"])
def enqueue():
    data = request.json
    sqs = boto3.resource('sqs', region_name='eu-west-1')
    queue = sqs.get_queue_by_name(QueueName='EpidemicSimulatorTasks')

    # Send message to SQS queue
    response = queue.send_message(
        # QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'populationSize': {
                'DataType': 'String',
                'StringValue': str(data['populationSize'])
            },
            'percentageStudents': {
                'DataType': 'Number',
                'StringValue': str(data['percentageStudents'])
            },
            'percentageWorkers': {
                'DataType': 'Number',
                'StringValue': str(data['percentageWorkers'])
            },
            'percentageStayHome': {
                'DataType': 'Number',
                'StringValue': str(data['percentageStayHome'])
            },
            'percentageElderly': {
                'DataType': 'Number',
                'StringValue': str(data['percentageElderly'])
            },
        },
        MessageBody=(
            'New Simulation Order'
        )
    )

    return response['MessageId']

if __name__ == '__main__':
    app.run(debug=True)

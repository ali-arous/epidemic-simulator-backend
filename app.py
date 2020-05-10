from flask import Flask, request, jsonify, redirect
import json
import boto3
from flask_awscognito import AWSCognitoAuthentication

app = Flask(__name__)

app.config['AWS_DEFAULT_REGION'] = 'eu-west-1'
app.config['AWS_COGNITO_DOMAIN'] = 'https://epidemic-simulator-login.auth.eu-west-1.amazoncognito.com'
app.config['AWS_COGNITO_USER_POOL_ID'] = 'eu-west-1_nb1h2zCRl'
app.config['AWS_COGNITO_USER_POOL_CLIENT_ID'] = '4o8211gnltlr3rcnbqgl0d93cv'
app.config['AWS_COGNITO_USER_POOL_CLIENT_SECRET'] = '1sp24inf8vpdckkkcibjeeo90uss9favgq4icdj41iqe1195b5d0'
app.config['AWS_COGNITO_REDIRECT_URL'] = 'https://127.0.0.1:5000/oauth2/idpresponse'

aws_auth = AWSCognitoAuthentication(app)

@app.route('/')
def hello_world():
    return 'Hello World! This is epidemic simulator backend  :)'

@app.route('/user-data', methods=["GET","POST"])
@aws_auth.authentication_required
def login():
    claims = aws_auth.claims
    return jsonify({'claims': claims})

@app.route('/oauth2/idpresponse', methods=["GET", "POST"])
def cognito_redirect():
    return "Yo Ali, this worked at least!"
    #access_token = aws_auth.get_access_token(request.args)
    #response = redirect(f"https://master.d2b045thd43tkr.amplifyapp.com/SignedIn/?{access_token}", code=302)
    #return response

@app.route('/order-simulation', methods=["POST"])
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

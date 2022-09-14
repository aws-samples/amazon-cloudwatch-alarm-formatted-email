import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info(f'event received: {event}')

    # Parse cloudwatch alarm JSON message
    message = json.loads(event['Records'][0]['Sns']['Message'])
    alarm_name = message['AlarmName']
    aws_account_id = message['AWSAccountId']
    region = message['Region']
    threshold = message['Trigger']['Threshold']
    new_state_reason = message['NewStateReason']
    state_change_time_full = message['StateChangeTime']
    state_change_time = state_change_time_full.split(".", 1)[0]
    dimensions = message['Trigger']['Dimensions']
    comparison_operator = message['Trigger']['ComparisonOperator']
    metric_current_value = new_state_reason[new_state_reason.find("[")+1:new_state_reason.find("[")+5]

    # Get instance-id from metric dimension
    try:
      dimension = next(item for item in dimensions if item['name'] == 'InstanceId')
      instance_id = dimension['value']
    except Exception as e:
        logger.error(f'Could not find EC2 instance-id in alarm event. Make sure Alarm is based on EC2 metric')
        raise e

    # Get SES configuration from lambda env variables
    email_template = os.environ['SES_TEMPLATE_CRITICAL']
    source_email = os.environ['EMAIL_SOURCE']
    destination_to_email = os.environ['EMAIL_TO_ADDRESSES']
    destination_cc_email = os.environ['EMAIL_CC_ADDRESSES']
    reply_to_email = os.environ['EMAIL_REPLY_TO_ADRESSES']

    # Read email addresses and send SES templated email
    ses = boto3.client('ses')
    try:
        response = ses.send_templated_email(
          Source=source_email,
          Destination={
            'ToAddresses': [
              destination_to_email,
            ],
            'CcAddresses': [
              destination_cc_email,
            ]
          },
          ReplyToAddresses=[
            reply_to_email,
          ],
          Template=email_template,
          TemplateData='{ \"alarm\":\"'+alarm_name+'\", \"reason\": \"'+new_state_reason+'\", \"account\": \"'+aws_account_id+'\", \"region\": \"'+region+'\", \"datetime\": \"'+state_change_time+'\", \"instanceId\": \"'+instance_id+'\", \"value\": \"'+str(metric_current_value)+'\", \"comparisonoperator\": \"'+comparison_operator+'\", \"threshold\": \"'+str(threshold)+'\" }'
        )
    except Exception as e:
        logger.error(f'Could not send SES templated email: {e}')
        raise
    else:
        logger.info(f'Alarm email notification successfully sent to {destination_to_email}')

"""Slack messaging functions."""

import os
import json

import requests


def send_slack_msg(text, channel, token, attachments=None, blocks=None, filepath=None):
    """Send a message to Slack.

    Parameters
    ----------
    text : string
        The message text.

    channel : string
        The channel to post the message to.

    token : string
        The Slack API access token.

    blocks : dict, optional
        Formatting blocks for the the message.
        NB a message can have blocks/attachments OR a file, not both.

    attachments : dict, optional
        Attachments to the message (technically deprecated).
        NB a message can have attachments/blocks OR a file, not both.

    filepath : string, optional
        A local path to a file to be added to the message.
        NB a message can have a file OR attachments/blocks, not both.


    """
    if (attachments is not None or blocks is not None) and filepath is not None:
        raise ValueError("A Slack message can't have both blocks and a file.")

    # Slack doesn't format attachments with markdown automatically
    if attachments:
        for attachment in attachments:
            if 'mrkdwn_in' not in attachment:
                attachment['mrkdwn_in'] = ['text']

        try:
            if not filepath:
                url = 'https://slack.com/api/chat.postMessage'
                payload = {'token': token,
                           'channel': channel,
                           'as_user': True,
                           'text': str(text),
                           'attachments': json.dumps(attachments) if attachments else None,
                           'blocks': json.dumps(blocks) if blocks else None,
                           }
                responce = requests.post(url, payload).json()
            else:
                url = 'https://slack.com/api/files.upload'
                filename = os.path.basename(filepath)
                name = os.path.splitext(filename)[0]
                payload = {'token': token,
                           'channels': channel,  # Note channel(s)
                           'as_user': True,
                           'filename': filename,
                           'title': name,
                           'initial_comment': text,
                           }
                with open(filepath, 'rb') as file:
                    responce = requests.post(url, payload, files={'file': file}).json()
            if not responce.get('ok'):
                if 'error' in responce:
                    raise Exception('Unable to send message: {}'.format(responce['error']))
                else:
                    raise Exception('Unable to send message')
        except Exception as err:
            print('Connection to Slack failed! - {}'.format(err))
            print('Message:', text)
            print('Attachments:', attachments)
            print('Blocks:', blocks)
            print('Filepath:', filepath)
    else:
        print('Slack Message:', text)
        print('Attachments:', attachments)
        print('Blocks:', blocks)
        print('Filepath:', filepath)

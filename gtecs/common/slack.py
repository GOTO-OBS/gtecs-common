"""Slack messaging functions."""

import json
import os

import requests


def send_message(text, channel, token,
                 attachments=None, blocks=None, filepath=None, return_link=False):
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

    return_link : bool, optional (default=False)
        If True, return a permalink URL to the posted message.

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
            response = requests.post(url, payload).json()
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
                response = requests.post(url, payload, files={'file': file}).json()

        if not response.get('ok'):
            if 'error' in response:
                raise Exception('Unable to send message: {}'.format(response['error']))
            else:
                raise Exception('Unable to send message')

    except Exception as err:
        print('Connection to Slack failed! - {}'.format(err))
        print('Message:', text)
        print('Attachments:', attachments)
        print('Blocks:', blocks)
        print('Filepath:', filepath)

    if return_link:
        if not filepath:
            message_ts = response['ts']
        else:
            # We want to get the timestamp of the message, not the file
            # It could be a public or private channel
            try:
                message_ts = response['file']['shares']['public'][channel][0]['ts']
            except KeyError:
                message_ts = response['file']['shares']['private'][channel][0]['ts']

        try:
            # Get permalink for the message identified by the timestamp
            url = 'https://slack.com/api/chat.getPermalink'
            payload = {'token': token,
                       'channel': channel,
                       'message_ts': message_ts,
                       }
            response = requests.post(url, payload).json()

            if not response.get('ok'):
                if 'error' in response:
                    raise Exception('Unable to retrieve permalink: {}'.format(response['error']))

            return response['permalink']

        except Exception as err:
            print('Unable to retrieve permalink - {}'.format(err))
    else:
        return response

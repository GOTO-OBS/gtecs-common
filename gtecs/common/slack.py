"""Slack messaging functions."""

import json
import os

import requests


def send_message(text, channel, token,
                 attachments=None, blocks=None, filepath=None,
                 username=None, icon_emoji=None,
                 return_link=False,
                 **kwargs):
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

    username : string, optional
        The username to post the message as, overwriting the default.
        Only works if a file is not being uploaded (ANNOYINGLY).

    icon_emoji : string, optional
        The emoji to use as the message poster's icon, overwriting the default.
        Note custom emoji need to have been added to the Slack workspace.
        Only works if a file is not being uploaded (ANNOYINGLY).

    return_link : bool, optional (default=False)
        If True, return a permalink URL to the posted message.

    Any other keyword arguments are passed to the message payload,
    see https://api.slack.com/methods/chat.postMessage
    or https://api.slack.com/methods/files.upload for details.

    """
    if (attachments is not None or blocks is not None) and filepath is not None:
        raise ValueError("A Slack message can't upload a file and include attachments/blocks.")
    if (username is not None or icon_emoji is not None) and filepath is not None:
        # I REALLY tried to get around this, but Slack just doesn't allow it.
        # You can only give the basic 'initial_comment' when uploading a file, which is much
        # more limited than a normal message. So when it's posted it uses the default username/icon.
        # I tried to upload the file first, then add an image block to the message.
        # But that doesn't work as the file is private until it is shared.
        # You can use files.sharedPublicURL to get a public URL, with some dodgy formatting
        # to get the correct link (see https://stackoverflow.com/a/57254520).
        # But that can't be called by bots, only users for some reason. I added the right scopes
        # under User Token Scopes in the Slack app settings, but then you have to use a different
        # token and the file still appears but posted with my username and profile!!!
        # See also https://github.com/slackapi/python-slack-sdk/issues/1228, no plans to change it,
        # and https://github.com/slackapi/python-slack-sdk/issues/1351 which details various
        # attempts to work around it all of which fail. Grrr.
        raise ValueError("A Slack message can't upload a file and include a custom username/icon.")

    # Slack doesn't format attachments with markdown automatically
    if attachments:
        for attachment in attachments:
            if 'mrkdwn_in' not in attachment:
                attachment['mrkdwn_in'] = ['text']

    # If blocks are included you can't give text, you have to add it as the first block.
    if blocks and text:
        blocks.insert(0, {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}})
        text = None

    try:
        if not filepath:
            url = 'https://slack.com/api/chat.postMessage'
            payload = {'token': token,
                       'channel': channel,
                       'text': str(text),
                       'attachments': json.dumps(attachments) if attachments else None,
                       'blocks': json.dumps(blocks) if blocks else None,
                       'username': username,
                       'icon_emoji': icon_emoji,
                       **kwargs,
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
                       'initial_comment': str(text),
                       **kwargs,
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
        return

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

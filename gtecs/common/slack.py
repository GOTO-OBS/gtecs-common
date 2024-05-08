"""Slack messaging functions."""

import json
import os
import time

from slack_sdk import WebClient


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
        client = WebClient(token=token)
        if not filepath:
            response = client.chat_postMessage(
                channel=channel,
                text=str(text),
                attachments=json.dumps(attachments) if attachments else None,
                blocks=json.dumps(blocks) if blocks else None,
                username=username,
                icon_emoji=icon_emoji,
                **kwargs,
            )
        else:
            response = client.files_upload_v2(
                channel=channel,
                initial_comment=str(text),
                file=filepath,
                filename=os.path.basename(filepath),
                title=os.path.splitext(os.path.basename(filepath))[0],
                **kwargs,
            )
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
        try:
            if not filepath:
                message_ts = response['ts']
            else:
                # We want to get the timestamp of the message, not the file
                # Annoyingly, with v2 Slack now scans all files and won't return the
                # sharing message immediately
                # (see https://github.com/slackapi/python-slack-sdk/issues/1329)
                # So we have to wait and check the file info until the message is available.
                shares = None
                if len(response['file']['shares']) != 0:
                    shares = response['file']['shares']
                else:
                    file_id = response['file']['id']
                    start_time = time.time()
                    timeout = 30
                    while not shares:
                        if time.time() - start_time > timeout:
                            raise TimeoutError('Timeout waiting for file to be shared')
                        response = client.files_info(file=file_id)
                        if len(response['file']['shares']) != 0:
                            shares = response['file']['shares']
                        time.sleep(0.5)

                share_type = list(shares.keys())[0]  # 'public' or 'private'
                if channel not in shares[share_type]:
                    raise ValueError('File not shared in correct channel?')
                message_ts = shares[share_type][channel][-1]['ts']  # Get the latest share ts

            # Get permalink for the message identified by the timestamp
            response = client.chat_getPermalink(
                channel=channel,
                message_ts=message_ts,
            )
            if not response.get('ok'):
                if 'error' in response:
                    raise Exception('Unable to retrieve permalink: {}'.format(response['error']))
                else:
                    raise Exception('Unable to send message')

            return response['permalink']

        except Exception as err:
            print('Unable to retrieve permalink - {}'.format(err))
    else:
        return response

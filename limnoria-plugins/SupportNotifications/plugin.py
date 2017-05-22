"""
Use GMail API to check an Inbox for new emails.

To generate the initial credentials you will need to execute this module from
python with first argument to a patch containing your API client details
and the second argument to the file where to store the credentials.

It uses the `historyID` configuration option to optimize the search.
It will start with searching all messages from Inbox and then will keep the
record of the history id.
So future runs and restarts should resume only from last history_id.

As long as there is no message in In
"""
from __future__ import print_function
from threading import Event, Thread

from supybot import (
    ircmsgs,
    )
from supybot.callbacks import ArgumentError, Plugin

import httplib2
from apiclient import discovery, errors
from oauth2client.file import Storage


class CancellableTimer(Thread):
    """
    A threaded timer which can be closed before the scheduled execution.
    """
    def __init__(self, delay, callback, *args, **kwargs):
        Thread.__init__(self)
        self._event = Event()
        self._step = 0.25
        self._remaining = delay / self._step

        self._callback = callback
        self._args = args
        self._kwargs = kwargs

    def run(self):
        while self._remaining > 0 and not self._event.is_set():
            self._remaining -= self._step
            self._event.wait(self._step)
        self._callback(*self._args, **self._kwargs)

    def cancel(self):
        self._event.set()


def get_credentials(credentials_path):
    """
    Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid it
    returns None.

    Returns:
        Credentials, the obtained credential or None
    """
    store = Storage(credentials_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        return None
    return credentials


class SupportNotifications(Plugin):
    """
    Send to the configured channel info about latest support activity.
    """
    threaded = True

    def __init__(self, irc):
        super(SupportNotifications, self).__init__(irc)
        self._irc = irc
        self._timer = None
        self._channel_name = None

        self._history_id = self.registryValue('historyID')

        self._interval = self.registryValue('pollInterval')

        self._target_address = self.registryValue('targetAddress').strip()
        self._team_domain = self.registryValue('teamDomain').strip()
        if not self._target_address:
            raise ArgumentError('targetAddress not configured.')
        if not self._team_domain:
            raise ArgumentError('teamDomain not configured.')

        credentials_path = self.registryValue('credentialsPath')
        credentials = get_credentials(credentials_path)
        if not credentials:
            raise ArgumentError('Failed to load API credentials.')

        http = credentials.authorize(httplib2.Http())
        self._google = discovery.build('gmail', 'v1', http=http, cache=False)

    def die(self):
        """
        Called when the plugin should end.
        """
        if self._timer is None:
            return

        self.log.info("Closing plugin. Cancelling the timer")
        self._timer.cancel()

    def do353(self, irc, msg):
        """
        Called when we have joined the channel.

        RPL_NAMREPLY - called when we have joined the channel and have
        received the list of members.
        """
        self._channel_name = msg.args[2]

        self.log.info(
            'Start polling for %s changes at %d seconds and sending to %s.' % (
            self._target_address, self._interval, self._channel_name))
        self._scheduleNextCheck()

    def _scheduleNextCheck(self):
        """
        Called to schedule the next API check.
        """
        if self._irc.zombie:
            # We are not connected.
            return

        if self._timer:
            return

        self._timer = CancellableTimer(self._interval, self._tick)
        self._timer.start()
        self.log.debug('Scheduling a new check.')

    def _tick(self):
        """
        Called when we should check for new emails.
        """
        if self._irc.zombie:
            # We are not connected.
            return

        self._checkInbox()
        # Schedule the next tick.
        self._timer = None
        self._scheduleNextCheck()

    def _checkInbox(self):
        """
        Emit changes for the new emails from inbox.
        """
        inbox_labels = [u'INBOX', u'UNREAD']
        details = None

        messages = self._getNewMessages()
        for message in messages:
            details = self._getMessageDetails(msg_id=message['id'])

            if set(inbox_labels) - set(details['labelIds']):
                # Not a unread message which is in Inbox.
                # Just ignore it for now.
                continue

            headers = {}
            for raw_header in details['payload']['headers']:
                headers[raw_header['name'].lower()] = raw_header['value']

            self._checkMessage(headers)
            # Any message is removed so that we will not process it later.
            self._trash(msg_id=message['id'])

        if details:
            self._history_id = int(details['historyId'])
            self.setRegistryValue('historyID', value=self._history_id)

    def _getNewMessages(self):
        """
        Return the new messages since the last run.
        """
        if self._history_id:
            return self._getMessagesFromHistory()
        else:
            return self._getMessagesFromInbox()

    def _getMessagesFromHistory(self):
        """
        Return the new messages based on account history.
        """
        start_history_id = self._history_id
        messages = []

        try:
            history = self._google.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes='messageAdded',
            ).execute()
            changes = history['history'] if 'history' in history else []
            for change in changes:
                messages.extend(change.get('messages', []))

            while 'nextPageToken' in history:
                page_token = history['nextPageToken']
                history = self._google.users().history().list(
                    userId='me',
                    startHistoryId=start_history_id,
                    historyTypes='messageAdded',
                    pageToken=page_token,
                    ).execute()

                for change in history['history']:
                    messages.extend(change.get('messages', []))

            return messages
        except errors.HttpError, error:
            self.log.error(
                '_getMessagesFromHistory: An error occurred: %s' % error)
            return []

    def _getMessagesFromInbox(self):
        """
        Return all the messages from Inbox.
        """
        label_ids = ['INBOX']
        messages = []

        try:
            response = self._google.users().messages().list(
                userId='me',
                labelIds=label_ids,
                ).execute()

            if 'messages' in response:
                messages.extend(response['messages'])

            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = self._google.users().messages().list(
                    userId='me',
                    labelIds=label_ids,
                    pageToken=page_token,
                    ).execute()
                messages.extend(response['messages'])

            return messages

        except errors.HttpError, error:
            self.log.error(
                '_getMessagesFromInbox: An error occurred: %s' % error)
            return []

    def _trash(self, msg_id):
        """
        Delete a message by sending it to trash..
        """
        try:
            self._google.users().messages().trash(
                userId='me', id=msg_id).execute()
        except errors.HttpError, error:
            self.log.error('_trash: An error occurred: %s' % error)

    def _getMessageDetails(self, msg_id):
        """
        Get a Message with given ID.
        """
        try:
            message = self._google.users().messages().get(
                userId='me', id=msg_id).execute()
            return message
        except errors.HttpError, error:
            self.log.error('_getMessageDetails: An error occurred: %s' % error)

    def _checkMessage(self, headers):
        """
        Check message to decide if we should send a notification.
        """
        to = headers.get('to', '')
        cc = headers.get('cc', '')
        if not (self._target_address in to or self._target_address in cc):
            # Not a message for our support email,
            return

        sender = headers.get('from', '')
        if self._team_domain not in sender:
            # No a message from our team
            return

        # We will ignore if the email is only to the internal team, that is
        # it does not have any outside TO or CC.
        has_outside = False

        for email in to.split('>, ') + cc.split('>, '):
            email = email.strip()
            if not email:
                continue

            if self._team_domain not in email:
                has_outside = True
                break

        if not has_outside:
            # Not a message outside the team.
            return

        subject = headers.get('subject', 'NO SUBJECT')
        self._sendStatus(sender, subject)

    def _sendStatus(self, sender, subject):
        """
        Send an IRC notification.
        """
        author = sender.split('@', 1)[0].split('<', 1)[1]

        self._irc.queueMsg(ircmsgs.notice(
            recipient=self._channel_name,
            s='[support-inbox][%s] Replied to: %s' % (author, subject),
            prefix='<support-notifications>',
            ))


Class = SupportNotifications

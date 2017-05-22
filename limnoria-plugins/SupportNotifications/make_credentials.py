"""
Helper to create the Google API credentials file via OAUTH-2.
"""
from __future__ import print_function
import sys

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


def save_credentials(client_path, credentials_path):
    """
    Do the browser OAuth-2 dance to generate credentials at `credentials_path`
    for client with details at `client_path`.
    """
    SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
    APPLICATION_NAME = 'Chevah Support IRC Notification'

    store = Storage(credentials_path)
    flow = client.flow_from_clientsecrets(client_path, SCOPES)
    flow.user_agent = APPLICATION_NAME
    tools.run_flow(flow, store)
    print('Storing credentials to ' + credentials_path)


if __name__ == '__main__':
    source = sys.argv[1]
    destination = sys.argv[2]
    # Oauth client will use use sys.argv for running the flow, so we clean
    # them.
    sys.argv = sys.argv[:1]
    save_credentials(source, destination)

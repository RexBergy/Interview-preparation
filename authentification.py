import google.oauth2.credentials
import google_auth_oauthlib.flow
import flask
import requests

def connect():
    # Required, call the from_client_secrets_file method to retrieve the client ID from a
    # client_secret.json file. The client ID (from that file) and access scopes are required. (You can
    # also use the from_client_config method, which passes the client configuration as it originally
    # appeared in a client secrets file but doesn't access the file itself.)
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('client_secret.json',
        scopes=['https://www.googleapis.com/auth/calendar.events.owned'])

    # Required, indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required. The value must exactly
    # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
    # configured in the API Console. If this value doesn't match an authorized URI,
    # you will get a 'redirect_uri_mismatch' error.
    flow.redirect_uri = 'http://localhost:8080/oauth2callback'

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Recommended, enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Optional, enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true',
        # Optional, set prompt to 'consent' will prompt the user for consent
        prompt='consent')

    return authorization_url

def fetch_token(url):
  
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('client_secret.json',
        scopes=['https://www.googleapis.com/auth/calendar.events.owned'])

    # Required, indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required. The value must exactly
    # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
    # configured in the API Console. If this value doesn't match an authorized URI,
    # you will get a 'redirect_uri_mismatch' error.
   # flow.redirect_uri = 'http://localhost:8080/oauth2callback'

    print("Here in fetch token")

   # response = requests.get(flow.redirect_uri)
    #flow.redirect_uri
    flow.redirect_uri = 'http://localhost:8080/oauth2callback'
    print("get request")
    authorization_response = url
    flow.fetch_token(authorization_response=authorization_response)
    print("got token")

    return flow.credentials
  


# state = flask.session['state']
# flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#     'client_secret.json',
#     scopes=['https://www.googleapis.com/auth/drive.metadata.readonly'],
#     state=state)
# flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

# authorization_response = flask.request.url
# flow.fetch_token(authorization_response=authorization_response)

# # Store the credentials in browser session storage, but for security: client_id, client_secret,
# # and token_uri are instead stored only on the backend server.
# credentials = flow.credentials
# flask.session['credentials'] = {
#     'token': credentials.token,
#     'refresh_token': credentials.refresh_token,
#     'granted_scopes': credentials.granted_scopes}

# # -*- coding: utf-8 -*-

# import os
# import flask
# import json
# import requests

# import google.oauth2.credentials
# import google_auth_oauthlib.flow
# import googleapiclient.discovery

# from gradio_client import Client

# client = Client("https://f21c5a511ed06cf0ea.gradio.live")

# # This variable specifies the name of a file that contains the OAuth 2.0
# # information for this application, including its client_id and client_secret.
# CLIENT_SECRETS_FILE = "client_secret.json"

# # The OAuth 2.0 access scope allows for access to the
# # authenticated user's account and requires requests to use an SSL connection.
# SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
#           'https://www.googleapis.com/auth/calendar.readonly']
# API_SERVICE_NAME = 'drive'
# API_VERSION = 'v2'

# app = flask.Flask(__name__)
# # Note: A secret key is included in the sample so that it works.
# # If you use this code in your application, replace this with a truly secret
# # key. See https://flask.palletsprojects.com/quickstart/#sessions.
# app.secret_key = 'REPLACE ME - this value is here as a placeholder.'

# @app.route('/')
# def index():
#   return print_index_table()

# @app.route('/drive')
# def drive_api_request():
#   if 'credentials' not in flask.session:
#     return flask.redirect('authorize')

#   features = flask.session['features']

#   if features['drive']:
#     # Load client secrets from the server-side file.
#     with open(CLIENT_SECRETS_FILE, 'r') as f:
#         client_config = json.load(f)['web']

#     # Load user-specific credentials from browser session storage.
#     session_credentials = flask.session['credentials']

#     # Reconstruct the credentials object.
#     credentials = google.oauth2.credentials.Credentials(
#         refresh_token=session_credentials.get('refresh_token'),
#         scopes=session_credentials.get('granted_scopes'),
#         token=session_credentials.get('token'),
#         client_id=client_config.get('client_id'),
#         client_secret=client_config.get('client_secret'),
#         token_uri=client_config.get('token_uri'))

#     drive = googleapiclient.discovery.build(
#         API_SERVICE_NAME, API_VERSION, credentials=credentials)

#     files = drive.files().list().execute()

#     # Save credentials back to session in case access token was refreshed.
#     flask.session['credentials'] = credentials_to_dict(credentials)

#     return flask.jsonify(**files)
#   else:
#     # User didn't authorize read-only Drive activity permission.
#     return '<p>Drive feature is not enabled.</p>'

# @app.route('/calendar')
# def calendar_api_request():
#   if 'credentials' not in flask.session:
#     return flask.redirect('authorize')

#   features = flask.session['features']

#   if features['calendar']:
#     # User authorized Calendar read permission.
#     # Calling the APIs, etc.
#     return ('<p>User granted the Google Calendar read permission. '+
#             'This sample code does not include code to call Calendar</p>')
#   else:
#     # User didn't authorize Calendar read permission.
#     # Update UX and application accordingly
#     return '<p>Calendar feature is not enabled.</p>'

# @app.route('/authorize')
# def authorize():
#   # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
#   flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#       CLIENT_SECRETS_FILE, scopes=SCOPES)

#   # The URI created here must exactly match one of the authorized redirect URIs
#   # for the OAuth 2.0 client, which you configured in the API Console. If this
#   # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
#   # error.
#   flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

#   authorization_url, state = flow.authorization_url(
#       # Enable offline access so that you can refresh an access token without
#       # re-prompting the user for permission. Recommended for web server apps.
#       access_type='offline',
#       # Enable incremental authorization. Recommended as a best practice.
#       include_granted_scopes='true')

#   # Store the state so the callback can verify the auth server response.
#   flask.session['state'] = state

#   return flask.redirect(authorization_url)

# @app.route('/oauth2callback')
# def oauth2callback():
#   # Specify the state when creating the flow in the callback so that it can
#   # verified in the authorization server response.
#   state = flask.session['state']

#   flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#       CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
#   flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

#   # Use the authorization server's response to fetch the OAuth 2.0 tokens.
#   authorization_response = flask.request.url
#   flow.fetch_token(authorization_response=authorization_response)

#   # Store credentials in the session.
#   # ACTION ITEM: In a production app, you likely want to save these
#   #              credentials in a persistent database instead.
#   credentials = flow.credentials
  
#   credentials = credentials_to_dict(credentials)
#   flask.session['credentials'] = credentials

#   # Check which scopes user granted
#   features = check_granted_scopes(credentials)
#   flask.session['features'] = features
#   return flask.redirect('/')
  
# @app.route('/revoke')
# def revoke():
#   if 'credentials' not in flask.session:
#     return ('You need to <a href="/authorize">authorize</a> before ' +
#             'testing the code to revoke credentials.')

#   # Load client secrets from the server-side file.
#   with open(CLIENT_SECRETS_FILE, 'r') as f:
#       client_config = json.load(f)['web']

#   # Load user-specific credentials from the session.
#   session_credentials = flask.session['credentials']

#   # Reconstruct the credentials object.
#   credentials = google.oauth2.credentials.Credentials(
#       refresh_token=session_credentials.get('refresh_token'),
#       scopes=session_credentials.get('granted_scopes'),
#       token=session_credentials.get('token'),
#       client_id=client_config.get('client_id'),
#       client_secret=client_config.get('client_secret'),
#       token_uri=client_config.get('token_uri'))

#   revoke = requests.post('https://oauth2.googleapis.com/revoke',
#       params={'token': credentials.token},
#       headers = {'content-type': 'application/x-www-form-urlencoded'})

#   status_code = getattr(revoke, 'status_code')
#   if status_code == 200:
#     # Clear the user's session credentials after successful revocation
#     if 'credentials' in flask.session:
#         del flask.session['credentials']
#         del flask.session['features']
#     return('Credentials successfully revoked.' + print_index_table())
#   else:
#     return('An error occurred.' + print_index_table())

# @app.route('/clear')
# def clear_credentials():
#   if 'credentials' in flask.session:
#     del flask.session['credentials']
#   return ('Credentials have been cleared.<br><br>' +
#           print_index_table())

# def credentials_to_dict(credentials):
#   return {'token': credentials.token,
#           'refresh_token': credentials.refresh_token,
#           'granted_scopes': credentials.granted_scopes}

# def check_granted_scopes(credentials):
#   features = {}
#   if 'https://www.googleapis.com/auth/drive.metadata.readonly' in credentials['granted_scopes']:
#     features['drive'] = True
#   else:
#     features['drive'] = False

#   if 'https://www.googleapis.com/auth/calendar.readonly' in credentials['granted_scopes']:
#     features['calendar'] = True
#   else:
#     features['calendar'] = False

#   return features

# def print_index_table():
#   return ('<table>' + 
#           '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
#           '<td>Go directly to the authorization flow. If there are stored ' +
#           '    credentials, you still might not be prompted to reauthorize ' +
#           '    the application.</td></tr>' +
#           '<tr><td><a href="/drive">Call Drive API directly</a></td>' +
#           '<td> Use stored credentials to call the API, you still might not be prompted to reauthorize ' +
#           '    the application.</td></tr>' +
#           '<tr><td><a href="/calendar">Call Calendar API directly</a></td>' +
#           '<td> Use stored credentials to call the API, you still might not be prompted to reauthorize ' +
#           '    the application.</td></tr>' + 
#           '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
#           '<td>Revoke the access token associated with the current user ' +
#           '    session. After revoking credentials, if you go to the test ' +
#           '    page, you should see an <code>invalid_grant</code> error.' +
#           '</td></tr>' +
#           '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
#           '<td>Clear the access token currently stored in the user session. ' +
#           '    After clearing the token, if you <a href="/authorize">authorize</a> ' +
#           '    again, you should go back to the auth flow.' +
#           '</td></tr></table>')

# if __name__ == '__main__':
#   # When running locally, disable OAuthlib's HTTPs verification.
#   # ACTION ITEM for developers:
#   #     When running in production *do not* leave this option enabled.
#   os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#   # This disables the requested scopes and granted scopes check.
#   # If users only grant partial request, the warning would not be thrown.
#   os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

#   # Specify a hostname and port that are set as a valid redirect URI
#   # for your API project in the Google API Console.
#   app.run('localhost', 8080, debug=True)
  
import os
import time
from flask import Blueprint, request, session
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from authlib.oidc.core import UserInfo
from .models import db, User, OAuth2Client
from .oauth2 import authorization, require_oauth
from .tnid import Tnid


bp = Blueprint('home', __name__)
tnid = Tnid(os.environ['TNID_CLIENT_ID'], os.environ['TNID_CLIENT_SECRET'])


def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None


@bp.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = current_user()
    if user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
    else:
        clients = []
    return render_template('home.html', user=user, clients=clients)


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('create_client.html')
    form = request.form
    client_id = gen_salt(24)
    client = OAuth2Client(client_id=client_id, user_id=user.id)
    # Mixin doesn't set the issue_at date
    client.client_id_issued_at = int(time.time())
    if client.token_endpoint_auth_method == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    }
    client.set_client_metadata(client_metadata)
    db.session.add(client)
    db.session.commit()
    return redirect('/')


# TODO: Store these in a database
votes = {'red': 7, 'blue': 5, 'green': 3, 'yellow': 2}

@bp.route('/poll', methods=['GET'])
def poll():
    if request.method == 'POST':
        color = request.form.get('color')
        if color in votes:
            votes[color] += 1
            session['vote'] = color
    return render_template('poll.html', vote=session.get('vote'), votes=votes)
    
@bp.route('/vote', methods=['GET', 'POST'])
def vote():
    # Do we have a vote?
    color = request.form.get('color', session.get('pending_vote'))
    if color in votes:
        # Are we logged in?
        user = current_user()
        if user is not None:
            # Logged in - record vote
            votes[color] += 1
            session['vote'] = color
            session.pop('pending_vote')
        else:
            # Not logged in - record pending vote and do authentication flow
            session['pending_vote'] = color
            return redirect('/oauth/authorize')
    return redirect('/poll')
    
# For development
@bp.route('/reset-vote', methods=['GET'])
def reset_vote():
    if 'vote' in session:
        votes[session['vote']] -= 1
    session.pop('vote')
    return redirect('/poll')

# For development
@bp.route('/logout', methods=['GET'])
def logout():
    session.pop('id')
    print(session['id'])
    return redirect('/poll')

@bp.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    if user is None:
        username = request.form.get('username')
        if username is not None:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                db.session.add(user)
                db.session.commit()
            if not tnid.invite(username):
                # Authentication failed
                return render_template('authorize.html')
            session['id'] = user.id
            # TODO: Remove hack to run on single server
            return redirect('/vote')
    if request.method == 'GET':
        try:
            grant = authorization.get_consent_grant(end_user=user)
        except OAuth2Error as error:
            # TODO: Remove hack to run on single server
            # return jsonify(dict(error.get_body()))
            class MyClient:
                client_name = 'TNID Voting App'
            class MyRequest:
                scope = 'openid profile'
            class MyGrant:
                client = MyClient()
                request = MyRequest()
            grant = MyGrant()
        return render_template('authorize.html', user=user, grant=grant)
    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
    if request.form['confirm'] == 'on':
        grant_user = user
    else:
        grant_user = None
    return authorization.create_authorization_response(grant_user=grant_user)


@bp.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@bp.route('/oauth/userinfo')
#@require_oauth('profile')
def api_me():
    # TODO: Remove hack to run on single server
    #user = current_token.user
    user = current_user()
    return jsonify(UserInfo(sub=str(user.id), phone_number=user.username, phone_number_verified=True))

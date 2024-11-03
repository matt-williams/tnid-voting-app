# TNID OpenID Connect Voting App

Heavily based on [example-oidc-server](https://github.com/authlib/example-oidc-server).

## Running

Install dependencies:

    $ pip install -r requirements.txt

Set Flask and Authlib environment variables:

    # disable check https (DO NOT SET THIS IN PRODUCTION)
    $ export AUTHLIB_INSECURE_TRANSPORT=1

Create Database and run the development server:

    $ flask initdb
    $ flask run

Now browse to `http://127.0.0.1:5000/poll`.

To check the OpenID user profile, browse to `http://127.0.0.1:5000/oauth/userinfo`

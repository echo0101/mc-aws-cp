import tweepy
from minecontrol import app,db,cache
from flask import redirect,url_for,request,session,abort,flash
from flask.ext.security import login_required, roles_accepted

from models import OAuthToken,SERVICE_TWITTER

@app.route("/setup/twitter/clear")
@login_required
@roles_accepted("admin")
def remove_twitter():
  access_token = db.session.query(OAuthToken).filter(OAuthToken.service==SERVICE_TWITTER).first()
  if access_token:
    db.session.delete(access_token)
    db.session.commit()
    flash("Removed Twitter account.")
  else:
    flash("No Twitter account setup.")
  return redirect(url_for("index"))
  

@app.route("/setup/twitter")
@login_required
@roles_accepted("admin")
def setup_twitter():
  auth = tweepy.OAuthHandler(
      app.config['TWITTER_TOKEN'], 
      app.config['TWITTER_SECRET'],
      app.config['MY_URL'] + '/api/v1/twitter/oauth')
  try:
    redirect_url = auth.get_authorization_url()
  except tweepy.TweepError:
    app.logger.warn('Twitter: Error! Failed to get request token.')
    abort(500)

  session['twitter_request_token']= (auth.request_token.key,
     auth.request_token.secret)

  return redirect(redirect_url)

@app.route("/api/v1/twitter/oauth")
@login_required
@roles_accepted("admin")
def twitter_handle_oauth():
  verifier = request.args.get('oauth_verifier', '')
  auth = tweepy.OAuthHandler(
      app.config['TWITTER_TOKEN'], 
      app.config['TWITTER_SECRET'])
  token = session['twitter_request_token']
  session.pop('twitter_request_token',None)
  auth.set_request_token(token[0], token[1])
  try:
    access_token = auth.get_access_token(verifier)
  except tweepy.TweepError:
    app.logger.warn('Twitter: Error! Failed to get access token.')
  token = db.session.query(OAuthToken).filter(OAuthToken.service==SERVICE_TWITTER).first() or \
    OAuthToken(
        service=SERVICE_TWITTER)
  token.key=auth.access_token.key
  token.secret=auth.access_token.secret
  db.session.add(token)
  db.session.commit()
  flash("Successfully Setup Twitter")
  return redirect(url_for("index"))

def get_screen_name():
  retval = cache.get('twitter_user')

  if not retval:
    access_token = db.session.query(OAuthToken).filter(OAuthToken.service==SERVICE_TWITTER).first()
    if access_token:
      auth = tweepy.OAuthHandler(
          app.config['TWITTER_TOKEN'], 
          app.config['TWITTER_SECRET'])
      auth.set_access_token(access_token.key, access_token.secret)
      api = tweepy.API(auth)
      retval = api.me().screen_name
      cache.set('twitter_user', retval, timeout=43200) # 30 days (in minutes)
  return retval

def tweet_msg(m):
  access_token = db.session.query(OAuthToken).filter(OAuthToken.service==SERVICE_TWITTER).first()
  if access_token:
    auth = tweepy.OAuthHandler(
        app.config['TWITTER_TOKEN'], 
        app.config['TWITTER_SECRET'])
    auth.set_access_token(access_token.key, access_token.secret)
    api = tweepy.API(auth)
    try:
      api.update_status(m)
    except tweepy.TweepError, e:
      app.logger.warn('Twitter: Tweet failed. %s', e) 


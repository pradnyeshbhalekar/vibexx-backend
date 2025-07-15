import flask
from flask import Flask, session, request, redirect, url_for, jsonify, Blueprint
from flask_session import Session
from login import spotify_login_bp
from playlist import playlist_bp
from detect_mood import detectmood_bp
from vibeplaylist import vibeplaylist_bp
from extension import mongo
import os
from flask_cors import CORS
from dotenv import load_dotenv


load_dotenv()



def create_app():
    app = Flask(__name__)
    CORS(app, origins=['http://localhost:3000','http://127.0.0.1:3000'],supports_credentials=True,methods=['GET','POST'])


    # mongo setup

    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        raise Exception("MONGO_URI not set in environment!")

    app.config["MONGO_URI"] = mongo_uri
    mongo.init_app(app)

    # Secret key for session management
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key")

    # Session Config
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    Session(app)



    # Register Blueprints
    app.register_blueprint(spotify_login_bp)
    app.register_blueprint(playlist_bp)
    app.register_blueprint(detectmood_bp)
    app.register_blueprint(vibeplaylist_bp)

    @app.route('/')
    def home():
        return "Welcome to the Spotify Auth App 🎧"

    return app

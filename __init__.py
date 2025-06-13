import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  

import logging
logging.basicConfig(level=logging.CRITICAL)

for lib in [
    "tensorflow", "matplotlib", "matplotlib.font_manager",  
]:
    logger = logging.getLogger(lib)
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False
    
    
from flask import Flask, session
from flask_session import Session
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

from .spotify_login import spotify_login_bp
from .playlist import playlist_bp
from .detect_mood import detectmood_bp



load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    CORS(app, origins=['http://localhost:3000','http://127.0.0.1:3000'])

    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    if not app.config['SECRET_KEY']:
        logging.error("FLASK_SECRET_KEY is not set in .env")
        raise ValueError("FLASK_SECRET_KEY must be set in .env")

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_NAME'] = 'session'  # Consistent cookie name
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False 
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'sessions')
    Session(app)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        os.chmod(app.config['SESSION_FILE_DIR'], 0o700)
        cache_path = os.path.join(app.instance_path, '.cache')
        if os.path.exists(cache_path):
            os.chmod(cache_path, 0o600)
        logging.debug(f"Created directories: {app.instance_path}, {app.config['SESSION_FILE_DIR']}")
    except OSError as e:
        logging.error(f"Failed to create directories: {e}")
        raise

    if test_config:
        app.config.from_mapping(test_config)
    else:
        app.config.from_pyfile("config.py", silent=True)

    app.register_blueprint(detectmood_bp)
    app.register_blueprint(spotify_login_bp)
    app.register_blueprint(playlist_bp)

    @app.route('/')
    def hello():
        logging.debug(f"Root route accessed, session: {dict(session)}")
        return "<h1>Hello, World!</h1>"

    return app
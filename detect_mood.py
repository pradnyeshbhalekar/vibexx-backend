from flask import Blueprint, request, jsonify
from fer import FER
import base64
from io import BytesIO
import numpy as np
import logging
from PIL import Image

detectmood_bp = Blueprint('detectmood', __name__, url_prefix='/detectmood')

def decode_image(image_data):
    image_data = image_data.split(',')[1]
    img_data = base64.b64decode(image_data)
    image = Image.open(BytesIO(img_data))
    return image

@detectmood_bp.route('/', methods=['POST'])
def detect_mood():
    try:
        data = request.get_json()
        if 'image' not in data:
            return jsonify({'error': 'Image data is missing'}), 400

        img_base64 = data['image']
        print("Received image data")

        image = decode_image(img_base64)
        image_np = np.array(image)

        detector = FER(mtcnn=True)
        emotion, score = detector.top_emotion(image_np)

        if emotion:
            response = {'emotion': emotion, 'score': score}
            print(f"Response: {response}")
            return jsonify(response)
        else:
            return jsonify({'error': 'No emotion detected'})

    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

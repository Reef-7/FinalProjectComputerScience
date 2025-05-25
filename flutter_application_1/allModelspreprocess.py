from flask import Flask, request, jsonify
import os
import cv2
import numpy as np
import tensorflow as tf
import pandas as pd
from flask_cors import CORS
from sklearn.preprocessing import MinMaxScaler
import pickle
import joblib
from sklearn.preprocessing import LabelEncoder
import threading
import time


app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


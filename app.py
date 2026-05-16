from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# متغير وهمي لعدد الزوار عشان يشتغل بدون قاعدة بيانات
visitors_count = 1542

@app.route('/')
def index():
    # بيشغل ملف index.html اللي برة علطول
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    global visitors_count
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'الرجاء إدخال رابط صحيح.'}), 400
        
        video_url = data['url']
        visitors_count += 1
        
        # الاتصال بسيرفر استخراج الروابط المباشر
        response = requests.get(f'https://api.v0.clideo.com/v1/analyze?url={video_url}', timeout=10)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'السيرفر الخارجي لا يستجيب حالياً.'}), 500
            
        result = response.json()
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'تعذر استخراج روابط لهذا الفيديو.'}), 400
            
        # نرجع البيانات للفرونت إند بنفس الشكل المتوقع
        return jsonify({
            'success': True,
            'title': result.get('title', 'فيديو بدون عنوان'),
            'thumbnail': result.get('thumbnail', ''),
            'options': result.get('options', []),
            'visitors_count': visitors_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'حدث خطأ في السيرفر: {str(e)}'}), 500

# مهم جداً لـ Vercel
app.debug = False

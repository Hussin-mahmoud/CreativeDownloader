from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__, template_folder='templates')
CORS(app)

unique_visitors = set()

# الهيدرز الثابتة لتقليد متصفح حقيقي 100%
FAKE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    'Sec-Fetch-Mode': 'no-cors',
}

@app.route('/')
def home():
    visitor_ip = request.remote_addr
    if visitor_ip:
        unique_visitors.add(visitor_ip)
    return render_template('index.html', visitors=max(len(unique_visitors), 1))

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'الرجاء إدخال رابط صحيح'}), 400
        
        video_url = data['url']
        
        visitor_ip = request.remote_addr
        if visitor_ip:
            unique_visitors.add(visitor_ip)
        
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'no_color': True,
            'http_headers': FAKE_HEADERS,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'video')
            thumbnail = info.get('thumbnail', '')
            formats = info.get('formats', [])
            
            options = []
            
            # جلب الجودات المدمجة
            for f in formats:
                if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    quality = f.get('format_note') or f.get('resolution') or 'تلقائية'
                    if not any(o['quality'] == str(quality) for o in options):
                        # السحر هنا: بنحول رابط التحميل لرابط محلي يمر عبر السيرفر بتاعنا منعاً للـ Access Denied
                        proxied_url = f"/api/proxy_download?url={requests.utils.quote(f.get('url'))}&ext={f.get('ext', 'mp4')}"
                        options.append({
                            'quality': str(quality),
                            'ext': f.get('ext', 'mp4'),
                            'type': 'فيديو وصورة',
                            'url': proxied_url
                        })
            
            # في حال منصات تيك توك وإنستا جلب الرابط المباشر الأحادي وتحويله لـ Proxy
            if not options and info.get('url'):
                proxied_url = f"/api/proxy_download?url={requests.utils.quote(info.get('url'))}&ext={info.get('ext', 'mp4')}"
                options.append({
                    'quality': 'جودة عالية HD',
                    'ext': info.get('ext', 'mp4'),
                    'type': 'فيديو وصورة',
                    'url': proxied_url
                })
            
            # جلب لينك الصوت وتحويله لـ Proxy
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            if audio_formats:
                best_audio = audio_formats[-1]
                if best_audio and best_audio.get('url'):
                    proxied_audio = f"/api/proxy_download?url={requests.utils.quote(best_audio.get('url'))}&ext=mp3"
                    options.append({
                        'quality': 'أعلى جودة صوت متاح',
                        'ext': 'mp3',
                        'type': 'صوت فقط (MP3)',
                        'url': proxied_audio
                    })
            
            return jsonify({
                'success': True,
                'title': title,
                'thumbnail': thumbnail,
                'options': options,
                'visitors_count': len(unique_visitors)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ السيرفر: {str(e)}'}), 500

# السيرفر الوسيط (Proxy) الذي يسحب الفيديو غصب عن سيرفر تيك توك وإنستا ويمرره لك كملف جاهز
@app.route('/api/proxy_download')
def proxy_download():
    target_url = request.args.get('url')
    ext = request.args.get('ext', 'mp4')
    if not target_url:
        return "رابط مفقود", 400
    
    try:
        # السيرفر بيعمل طلب حقيقي بهيدرز قوية جداً لتخطي حظر السيرفرات
        req = requests.get(target_url, headers=FAKE_HEADERS, stream=True, timeout=30)
        
        # تمرير الداتا لايف للمتصفح كملف تحميل مباشر بدلاً من فتحه كصفحة ويب
        def generate():
            for chunk in req.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
                    
        headers = {
            'Content-Type': req.headers.get('Content-Type', 'video/mp4'),
            'Content-Disposition': f'attachment; filename="creative_download_{unique_visitors.__len__()}.{ext}"'
        }
        return Response(generate(), headers=headers)
    except Exception as e:
        return f"فشل تخطي الحماية: {str(e)}", 500
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
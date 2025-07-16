#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import threading
import time
from datetime import datetime
import zipfile
import io
from manyo_beef_scraper import ManyoBeefScraper

app = Flask(__name__)

# Global variables for tracking scraping status
scraping_status = {
    'is_running': False,
    'progress': 0,
    'message': '',
    'completed': False,
    'error': None,
    'results_available': False
}

def run_scraper_background():
    """Run scraper in background thread"""
    global scraping_status
    
    try:
        scraping_status['is_running'] = True
        scraping_status['progress'] = 0
        scraping_status['message'] = '初始化爬蟲...'
        scraping_status['error'] = None
        
        # Initialize scraper
        scraper = ManyoBeefScraper(headless=True)
        
        scraping_status['progress'] = 10
        scraping_status['message'] = '搜尋餐廳中...'
        
        # Search for restaurants
        restaurant_urls = scraper.search_restaurants()
        
        if not restaurant_urls:
            scraping_status['error'] = '未找到餐廳，請檢查搜尋條件'
            scraping_status['is_running'] = False
            return
        
        scraping_status['progress'] = 30
        scraping_status['message'] = f'找到 {len(restaurant_urls)} 家餐廳，開始提取資訊...'
        
        # Extract information for each restaurant
        total_restaurants = len(restaurant_urls)
        for i, url in enumerate(restaurant_urls):
            scraping_status['progress'] = 30 + (i / total_restaurants) * 60
            scraping_status['message'] = f'處理餐廳 {i+1}/{total_restaurants}'
            
            restaurant_info = scraper.extract_restaurant_info(url)
            if restaurant_info:
                scraper.restaurants.append(restaurant_info)
            
            time.sleep(2)  # Be respectful to the server
        
        scraping_status['progress'] = 90
        scraping_status['message'] = '保存資料中...'
        
        # Save data
        scraper.save_data()
        
        scraping_status['progress'] = 100
        scraping_status['message'] = f'完成！共找到 {len(scraper.restaurants)} 家餐廳的資料'
        scraping_status['completed'] = True
        scraping_status['results_available'] = True
        
        # Close scraper
        scraper.close()
        
    except Exception as e:
        scraping_status['error'] = str(e)
        scraping_status['message'] = f'錯誤：{str(e)}'
    finally:
        scraping_status['is_running'] = False

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start scraping process"""
    global scraping_status
    
    if scraping_status['is_running']:
        return jsonify({
            'success': False,
            'message': '爬蟲已在運行中'
        })
    
    # Reset status
    scraping_status = {
        'is_running': False,
        'progress': 0,
        'message': '',
        'completed': False,
        'error': None,
        'results_available': False
    }
    
    # Start scraping in background thread
    thread = threading.Thread(target=run_scraper_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': '爬蟲已啟動'
    })

@app.route('/status')
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)

@app.route('/download/<file_type>')
def download_file(file_type):
    """Download results file"""
    if not scraping_status['results_available']:
        return jsonify({
            'success': False,
            'message': '沒有可下載的結果'
        })
    
    if file_type == 'json':
        if os.path.exists('manyo_beef_restaurants.json'):
            return send_file('manyo_beef_restaurants.json', as_attachment=True)
    elif file_type == 'csv':
        if os.path.exists('manyo_beef_restaurants.csv'):
            return send_file('manyo_beef_restaurants.csv', as_attachment=True)
    elif file_type == 'all':
        # Create zip file with both JSON and CSV
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists('manyo_beef_restaurants.json'):
                zf.write('manyo_beef_restaurants.json')
            if os.path.exists('manyo_beef_restaurants.csv'):
                zf.write('manyo_beef_restaurants.csv')
        
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='manyo_beef_restaurants.zip'
        )
    
    return jsonify({
        'success': False,
        'message': '文件不存在'
    })

@app.route('/results')
def view_results():
    """View results in browser"""
    if not scraping_status['results_available']:
        return jsonify({
            'success': False,
            'message': '沒有可查看的結果'
        })
    
    try:
        with open('manyo_beef_restaurants.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return render_template('results.html', restaurants=data)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'讀取結果失敗：{str(e)}'
        })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=8000, debug=False)
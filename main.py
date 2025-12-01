import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import json
import threading
import time
from underthesea import word_tokenize, ner
from datetime import datetime, timedelta
import re
import unicodedata
import os
import sys

class VietnameseNLPProcessor:
    """Bộ xử lý NLP tiếng Việt"""
    
    def __init__(self):
        # Từ khóa để xác định các phần của câu (có dấu và không dấu)
        self.reminder_patterns = [
            # PHÚT - Có dấu
            r'nhắc\s+(tôi|mình)?\s*trước\s*(\d+)\s*phút',
            r'nhắc\s+nhở\s*trước\s*(\d+)\s*phút',
            r'báo\s+trước\s*(\d+)\s*phút',
            r'trước\s*(\d+)\s*phút',
            
            # PHÚT - Không dấu
            r'nhac\s+(toi|minh)?\s*truoc\s*(\d+)\s*phut',
            r'nhac\s+nho\s*truoc\s*(\d+)\s*phut',
            r'bao\s*truoc\s*(\d+)\s*phut',
            r'truoc\s*(\d+)\s*phut',
            
            # GIỜ - Có dấu
            r'nhắc\s+(tôi|mình)?\s*trước\s*(\d+)\s*giờ',
            r'nhắc\s+nhở\s*trước\s*(\d+)\s*giờ',
            r'báo\s+trước\s*(\d+)\s*giờ',
            r'trước\s*(\d+)\s*giờ',
            
            # GIỜ - Không dấu
            r'nhac\s+(toi|minh)?\s*truoc\s*(\d+)\s*gio',
            r'nhac\s+nho\s*truoc\s*(\d+)\s*gio',
            r'bao\s*truoc\s*(\d+)\s*gio',
            r'truoc\s*(\d+)\s*gio',
            
            # PHÚT - Viết tắt (p)
            r'nhắc\s+(tôi|mình)?\s*trước\s*(\d+)\s*p',
            r'nhắc\s+nhở\s*trước\s*(\d+)\s*p',
            r'trước\s*(\d+)\s*p',
            
            # PHÚT - Không đơn vị (mặc định phút)
            r'nhắc\s+(tôi|mình)?\s*trước\s*(\d+)',
            r'nhắc\s+nhở\s*trước\s*(\d+)',
            r'trước\s*(\d+)\s*$'
        ]
        
    def remove_accents(self, text):
        """Chuyển đổi tiếng Việt có dấu thành không dấu"""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    def normalize_text(self, text):
        """Chuẩn hóa văn bản"""
        # Chuyển về chữ thường
        text = text.lower().strip()
        
        # Thứ hai tới → thứ 2 tuần tới
        text = re.sub(r'\bthu\s+([0-9]+|[a-z]+)\s+\btoi\b', r'thứ \1 tuần tới', text)

        # Chuẩn hóa các từ viết tắt (cả có dấu và không dấu)
        text = re.sub(r'\bnhắc tôi\b', 'nhắc', text)
        text = re.sub(r'\bnhắc mình\b', 'nhắc', text)
        text = re.sub(r'\bnhac toi\b', 'nhắc', text)
        text = re.sub(r'\bnhac minh\b', 'nhắc', text)
        text = re.sub(r'\bnhac\b', 'nhắc', text)
        text = re.sub(r'\bnahc\b', 'nhắc', text)
        text = re.sub(r'\btruoc\b', 'trước', text)

        # Chuẩn hóa thời gian
        text = re.sub(r'(\d+)\s*gio\b', r'\1 giờ', text)  # Bỏ \b ở sau gio
        text = re.sub(r'(\d+)\s*g\b', r'\1 giờ', text)
        text = re.sub(r'(\d+)\s*h\b', r'\1 giờ', text)
        text = re.sub(r'(\d+)\s*phut\b', r'\1 phút', text)
        text = re.sub(r'(\d+)\s*p\b', r'\1 phút', text)

        #Chuẩn hóa thứ
        text = re.sub(r'\bthu hai\b', 'thứ hai', text)
        text = re.sub(r'\bthu ba\b', 'thứ ba', text)
        text = re.sub(r'\bthu tu\b', 'thứ tư', text)
        text = re.sub(r'\bthu nam\b', 'thứ năm', text)
        text = re.sub(r'\bthu sau\b', 'thứ sáu', text)
        text = re.sub(r'\bthu bay\b', 'thứ bảy', text)
        text = re.sub(r'\bchu nhat\b', 'chủ nhật', text)
        text = re.sub(r'\bchu nhat toi\b', 'chủ nhật tuần tới', text)
        
        #Chuyển "X giờ Y" thành "X:Y" trước khi xử lý khác
        text = re.sub(r'(\d+)\s*(giờ|h|gio)\s*(\d+)\b', r'\1:\3', text)
        
        return text
    
    def preprocess_text(self, text):
        """Tiền xử lý văn bản với hỗ trợ không dấu"""
        # Chuẩn hóa văn bản
        normalized_text = self.normalize_text(text)
        
        # Sử dụng word_tokenize từ Underthesea để tách từ
        try:
            tokens = word_tokenize(normalized_text)
            processed_text = ' '.join(tokens)
            # Sửa lỗi: gộp lại các số thời gian bị tách bởi dấu :
            # Ví dụ: "9 : 30" → "9:30"
            processed_text = re.sub(r'(\d+)\s*:\s*(\d+)', r'\1:\2', processed_text)
        except:
            # Fallback: tự tách từ đơn giản nếu Underthesea lỗi
            processed_text = normalized_text
        
        return processed_text
    

    def extract_reminder_minutes(self, text):
        """Trích xuất thời gian nhắc nhở"""
        # Chuẩn hóa text trước khi xử lý
        normalized_text = self.normalize_text(text)
        
        for pattern in self.reminder_patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                # Lấy số từ group phù hợp
                groups = match.groups()
                for group in groups:
                    if group and group.isdigit():
                        number = int(group)
                        
                        # Kiểm tra đơn vị
                        # Nếu pattern chứa "giờ" hoặc "gio" → nhân 60
                        if re.search(r'giờ|gio', pattern, re.IGNORECASE):
                            return number * 60
                        # Nếu pattern chứa "phút", "phut", hoặc "p" → giữ nguyên
                        elif re.search(r'phút|phut|p', pattern, re.IGNORECASE):
                            return number
                        else:
                            # Mặc định là phút
                            return number
                
                # Nếu không tìm thấy số trong groups, thử tìm trong toàn bộ match
                full_match = re.search(r'(\d+)', match.group())
                if full_match:
                    number = int(full_match.group(1))
                    # Kiểm tra đơn vị từ pattern
                    if re.search(r'giờ|gio', pattern, re.IGNORECASE):
                        return number * 60
                    else:
                        return number
        
        return 0
    
    def extract_event_name(self, text):
        """Trích xuất tên sự kiện"""
        # Chuẩn hóa text
        normalized_text = self.normalize_text(text)
        clean_text = normalized_text
        
        # Bước 1: Loại bỏ phần nhắc nhở
        clean_text = re.sub(r',\s*nhắc\s*(tôi|mình)?\s*trước\s*\d+\s*phút\s*\.?', '', clean_text)
        clean_text = re.sub(r'\s*nhắc\s*(tôi|mình)?\s*trước\s*\d+\s*phút\s*\.?$', '', clean_text)
        clean_text = re.sub(r',\s*nhac\s*(toi|minh)?\s*truoc\s*\d+\s*phut\s*\.?', '', clean_text)
        clean_text = re.sub(r'\s*nhac\s*(toi|minh)?\s*truoc\s*\d+\s*phut\s*\.?$', '', clean_text)
        
        # Bước 2: Loại bỏ "nhắc" ở đầu câu
        clean_text = re.sub(r'^nhắc\s+', '', clean_text)
        clean_text = re.sub(r'^nhac\s+', '', clean_text)
        
        # Bước 3: Tìm tất cả các từ khóa phân cách (thời gian và địa điểm)
        separator_patterns = [
            # Thời gian
            r'lúc\s+\d+', r'vào\s+lúc\s+\d+', r'vào\s+\d+', 
            r'\d+\s*(giờ|h|gio)', r'\d+:\d+', r'\d+\s*(sáng|chiều|tối|sang|chieu|toi)',
            r'luc\s+\d+', r'vao\s+luc\s+\d+', r'vao\s+\d+',
            # Địa điểm
            r'ở\s+', r'tại\s+', r'\bo\s+', r'tai\s+'
        ]
        
        # Tìm vị trí của tất cả các separator
        separator_positions = []
        for pattern in separator_patterns:
            matches = re.finditer(pattern, clean_text)
            for match in matches:
                separator_positions.append({
                    'position': match.start(),
                    'type': 'time' if any(time_word in pattern for time_word in ['lúc', 'vào', 'giờ', 'gio', 'sáng', 'chiều', 'tối']) else 'location',
                    'pattern': pattern
                })
        
        # Sắp xếp theo vị trí
        separator_positions.sort(key=lambda x: x['position'])
        
        # Bước 4: Tìm separator đầu tiên (có thể là thời gian HOẶC địa điểm)
        if separator_positions:
            first_separator = separator_positions[0]
            first_separator_pos = first_separator['position']
            
            # Lấy phần trước separator đầu tiên làm tên sự kiện
            event_part = clean_text[:first_separator_pos].strip()
            
            # Làm sạch: loại bỏ các từ không cần thiết ở cuối
            event_part = re.sub(r'\s*(ở|tại|\bo\b|tai|và|va|,)\s*$', '', event_part)
            event_part = event_part.strip()
            
            # Nếu event_part có ý nghĩa, trả về
            if event_part and len(event_part) > 1 and event_part not in ['vào', 'ở']:
                return event_part
        
        # Fallback: tìm phần trước dấu phẩy đầu tiên
        parts = clean_text.split(',')
        if len(parts) > 1 and parts[0].strip():
            event_part = parts[0].strip()
            event_part = re.sub(r'\s*(ở|tại|o|tai|và|va)\s*$', '', event_part)
            if event_part and len(event_part) > 1:
                return event_part
        
        # Fallback cuối cùng: lấy 3-4 từ đầu tiên làm tên sự kiện
        words = clean_text.split()
        if len(words) >= 2:
            # Tránh lấy các từ không có nghĩa
            meaningful_words = [w for w in words if w not in ['vào', 'ở', 'tại', 'o', 'tai', 'và', 'va']]
            if meaningful_words:
                event_part = ' '.join(meaningful_words[:min(3, len(meaningful_words))])
                return event_part
        
        return "Sự kiện không xác định"
    
    def extract_location(self, text):
        """Trích xuất địa điểm"""
        normalized_text = self.normalize_text(text)
        
        # Pattern cải tiến: lấy toàn bộ phần sau "ở/tại" cho đến khi gặp dấu phẩy hoặc từ khóa thời gian
        location_patterns = [
            r'(?:ở|tại|\bo|tai)\s+([^,]*?)(?=\s*(,|\s+lúc|\s+vào|\s+nhắc|\s+nhac|\s*\d+\s*(giờ|h|gio)|\s*$))',
            r'(?:ở|tại|\bo|tai)\s+([^,]*)'
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, normalized_text)
            if location_match:
                location = location_match.group(1).strip()
                
                # Làm sạch: loại bỏ các từ thừa nhưng GIỮ LẠI số phòng
                # Chỉ loại bỏ nếu các từ này đứng RIÊNG LẺ ở cuối
                location = re.sub(r'\s+(mai|nay|ngày mai|hôm nay|và|va)$', '', location)
                location = re.sub(r'\s+(lúc|vào|luc|vao).*$', '', location)  # QUAN TRỌNG: chỉ xóa nếu có từ khóa thời gian sau
                location = location.strip()
                
                # Kiểm tra xem location có chứa thông tin hữu ích không
                if location and len(location) > 1:
                    # Loại bỏ nếu location chỉ là số đơn thuần hoặc từ không có nghĩa
                    if (not re.match(r'^\d+$', location) and 
                        location not in ['sang', 'chieu', 'toi', 'sáng', 'chiều', 'tối']):
                        return location
        return ""
    
    def parse_time(self, text):
        """Phân tích thời gian - Bổ sung hiểu ngày trong tuần"""
        normalized_text = self.normalize_text(text)
        now = datetime.now()
        
        # Xác định ngày dựa trên các từ khóa đặc biệt
        target_date = self.determine_target_date(normalized_text, now)
        
        # Tìm thời gian bắt đầu và kết thúc
        start_time = None
        end_time = None
        
        # Tìm tất cả các thời gian trong câu
        all_times = self.find_all_times(normalized_text)
        
        # Sắp xếp theo vị trí trong câu
        all_times.sort(key=lambda x: x['position'])
        
        # Thời gian đầu tiên là start_time
        if all_times:
            first_time = all_times[0]
            try:
                start_time = target_date.replace(hour=first_time['hour'], minute=first_time['minute'], second=0, microsecond=0)
                # Nếu thời gian đã qua và không phải là ngày đặc biệt, chuyển sang ngày mai
                if start_time < now and not self.is_special_date_keyword(normalized_text):
                    start_time += timedelta(days=1)
            except ValueError:
                start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # QUAN TRỌNG: Chỉ set end_time khi có từ khóa kết thúc RÕ RÀNG
        has_clear_end_keyword = any(word in normalized_text for word in ['kết thúc', 'ket thuc'])
        
        if len(all_times) >= 2 and has_clear_end_keyword:
            second_time = all_times[1]
            try:
                end_time = target_date.replace(hour=second_time['hour'], minute=second_time['minute'], second=0, microsecond=0)
                # Đảm bảo end_time không nhỏ hơn start_time
                if start_time and end_time <= start_time:
                    end_time = end_time.replace(hour=end_time.hour + 12)
            except ValueError:
                pass
        else:
            # KHÔNG có thời gian kết thúc rõ ràng
            end_time = None
        
        # Nếu không tìm thấy start_time, dùng mặc định
        if not start_time:
            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return start_time, end_time

    def determine_target_date(self, text, now):
        """Xác định ngày mục tiêu dựa trên từ khóa"""
        # Ngày trong tuần
        weekday_map = {
            'thứ 2': 0, 'thứ hai': 0, 
            'thứ 3': 1, 'thứ ba': 1, 
            'thứ 4': 2, 'thứ tư': 2, 
            'thứ 5': 3, 'thứ năm': 3, 
            'thứ 6': 4, 'thứ sáu': 4, 
            'thứ 7': 5, 'thứ bảy': 5,
            'chủ nhật': 6, 'cn': 6 
        }
        
        current_weekday = now.weekday()
        
        # Kiểm tra các trường hợp đặc biệt
        for keyword, target_weekday in weekday_map.items():
            if keyword in text:
                days_ahead = target_weekday - current_weekday
                # Kiểm tra "tuần tới", "tuần sau"
                if any(word in text for word in ['tuần sau', 'tuan sau']):
                    days_ahead += 7
                if any(word in text for word in ['tuần tới',  'tuan toi']):
                    days_ahead += 14
                
                return now + timedelta(days=days_ahead)
        
        # Cuối tuần (thứ 7 hoặc chủ nhật tuần này)
        if any(word in text for word in ['cuối tuần', 'cuoi tuan']):
            days_to_saturday = 5 - current_weekday  # Thứ 7 = 5
            if days_to_saturday < 0:
                days_to_saturday += 7
            return now + timedelta(days=days_to_saturday)
        
        # Đầu tuần (thứ 2 tuần này hoặc tuần sau)
        if any(word in text for word in ['đầu tuần', 'dau tuan']):
            days_to_monday = 0 - current_weekday  # Thứ 2 = 0
            if days_to_monday <= 0:
                days_to_monday += 7
            return now + timedelta(days=days_to_monday)
        
        # Giữa tuần (thứ 3, 4, 5)
        if any(word in text for word in ['giữa tuần', 'giua tuan']):
            # Mặc định là thứ 4
            days_to_wednesday = 2 - current_weekday  # Thứ 4 = 2
            if days_to_wednesday <= 0:
                days_to_wednesday += 7
            return now + timedelta(days=days_to_wednesday)
        
        # Ngày mai
        if any(word in text for word in ['mai', 'ngày mai']):
            return now + timedelta(days=1)
        
        if any(word in text for word in ['ngày kia']):
            return now + timedelta(days=2)
        
        # Hôm nay
        if any(word in text for word in ['nay', 'hôm nay']):
            return now
        
        # Mặc định là hôm nay
        return now

    def find_all_times(self, text):
        """Tìm tất cả các thời gian trong câu"""
        all_times = []
        
        # Pattern để tìm tất cả thời gian - THÊM PATTERN MỚI
        time_patterns = [
            r'(?:lúc|vào|luc|vao)?\s*(\d+)\s*(sáng|chiều|tối|sang|chieu|toi)',
            r'(\d+)\s*(giờ|h|gio)\s*(sáng|chiều|tối|sang|chieu|toi)?',
            r'(\d+):(\d+)',
            r'(\d+)\s*h\b'
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                hour, minute = self.extract_hour_minute(match)
                if hour is not None:
                    all_times.append({
                        'hour': hour,
                        'minute': minute,
                        'position': match.start(),
                        'text': match.group(),
                        'pattern': pattern
                    })
        
        return all_times

    def is_special_date_keyword(self, text):
        """Kiểm tra xem có từ khóa ngày đặc biệt không"""
        special_keywords = [
            'thứ 2', 'thứ hai', 'thứ 3', 'thứ ba', 'thứ 4', 'thứ tư', 'thứ 5', 'thứ năm',
            'thứ 6', 'thứ sáu', 'thứ 7', 'thứ bảy', 'chủ nhật', 'cn',
            'cuối tuần', 'cuoi tuan', 'đầu tuần', 'dau tuan', 'giữa tuần', 'giua tuan',
            'tuần tới', 'tuần sau', 'tuan toi', 'tuan sau'
        ]
        
        return any(keyword in text for keyword in special_keywords)
    
    def extract_hour_minute(self, match):
        """Trích xuất giờ và phút từ match object - FIXED"""
        hour, minute = None, 0
        
        if match:
            groups = match.groups()
            
            # Pattern 1: "10:30"
            if len(groups) >= 2 and groups[0] and groups[0].isdigit() and groups[1] and groups[1].isdigit():
                if ':' in match.group():
                    hour = int(groups[0])
                    minute = int(groups[1])
                    # Kiểm tra giờ hợp lệ (0-23)
                    if 0 <= hour <= 23:
                        return hour, minute
                    return None, 0
            
            # Pattern 2: "10 sáng" 
            elif len(groups) >= 2 and groups[0] and groups[0].isdigit():
                hour = int(groups[0])
                if len(groups) >= 2 and groups[1] and groups[1] in ['sáng', 'chiều', 'tối', 'sang', 'chieu', 'toi']:
                    # KIỂM TRA: "30 sáng" là không hợp lệ (giờ không thể là 30)
                    if hour > 12:  # Giờ không hợp lệ cho pattern này
                        return None, 0
                    period = groups[1]
                    hour = self.adjust_hour_for_period(hour, period)
                    return hour, minute
            
            # Pattern 3: "10 giờ"
            elif len(groups) >= 1 and groups[0] and groups[0].isdigit():
                hour = int(groups[0])
                if len(groups) >= 3 and groups[2] and groups[2] in ['sáng', 'chiều', 'tối', 'sang', 'chieu', 'toi']:
                    period = groups[2]
                    hour = self.adjust_hour_for_period(hour, period)
                    return hour, minute
        
        return hour, minute
    
    def adjust_hour_for_period(self, hour, period):
        """Điều chỉnh giờ theo buổi trong ngày"""
        if period in ['chiều', 'chieu'] and hour < 12:
            return hour + 12
        elif period in ['tối', 'toi'] and hour < 12:
            return hour + 12
        elif period in ['sáng', 'sang'] and hour == 12:
            return 0
        return hour
    
    def process_text(self, text):
        """Xử lý toàn bộ văn bản"""
        try:
            # Component 1: Preprocessing
            processed_text = self.preprocess_text(text)
            print(f"After preprocessing: '{processed_text}'")
            
            # Component 2: Trích xuất thông tin
            event_name = self.extract_event_name(processed_text)
            
            location = self.extract_location(processed_text)
            
            reminder_minutes = self.extract_reminder_minutes(processed_text)
            
            # Component 3: Phân tích thời gian
            start_time, end_time = self.parse_time(processed_text)
            
            # Component 4: Hợp nhất kết quả
            result = {
                "event": event_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat() if end_time else None,
                "location": location,
                "reminder_minutes": reminder_minutes
            }
            return result
            
        except Exception as e:
            return {"error": f"Lỗi xử lý: {str(e)}"}

class DatabaseManager:
    """Quản lý cơ sở dữ liệu SQLite"""
    
    def __init__(self, db_path="schedule.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                location TEXT,
                reminder_minutes INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_event(self, event_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (event_name, start_time, end_time, location, reminder_minutes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            event_data["event"],
            event_data["start_time"],
            event_data["end_time"],
            event_data["location"],
            event_data["reminder_minutes"]
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self, date_filter=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if date_filter:
            cursor.execute('''
                SELECT * FROM events 
                WHERE date(start_time) = date(?)
                ORDER BY start_time
            ''', (date_filter,))
        else:
            cursor.execute('''
                SELECT * FROM events 
                ORDER BY start_time
            ''')
        
        events = cursor.fetchall()
        conn.close()
        return events
    
    def update_event(self, event_id, event_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE events 
            SET event_name = ?, start_time = ?, end_time = ?, location = ?, reminder_minutes = ?
            WHERE id = ?
        ''', (
            event_data["event"],
            event_data["start_time"],
            event_data["end_time"],
            event_data["location"],
            event_data["reminder_minutes"],
            event_id
        ))
        
        conn.commit()
        conn.close()
    
    def delete_event(self, event_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        conn.close()
    
    def search_events(self, keyword):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM events 
            WHERE event_name LIKE ? OR location LIKE ?
            ORDER BY start_time
        ''', (f'%{keyword}%', f'%{keyword}%'))
        
        events = cursor.fetchall()
        conn.close()
        return events

class ReminderSystem:
    """Hệ thống nhắc nhở"""
    
    def __init__(self, db_manager, gui_callback):
        self.db_manager = db_manager
        self.gui_callback = gui_callback
        self.is_running = False
        self.thread = None
    
    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._check_reminders, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.is_running = False
    
    def _check_reminders(self):
        while self.is_running:
            try:
                events = self.db_manager.get_events()
                current_time = datetime.now()
                
                for event in events:
                    event_id, event_name, start_time_str, end_time, location, reminder_minutes, created_at = event
                    start_time = datetime.fromisoformat(start_time_str)
                    
                    reminder_time = start_time - timedelta(minutes=reminder_minutes)
                    
                    if current_time >= reminder_time and current_time < reminder_time + timedelta(minutes=1):
                        self.gui_callback(f"Sắp diễn ra: {event_name}\nThời gian: {start_time.strftime('%H:%M %d/%m/%Y')}\nĐịa điểm: {location}")
                
                time.sleep(60)
            except Exception as e:
                print(f"Lỗi hệ thống nhắc nhở: {e}")
                time.sleep(60)

class ScheduleApp:
    """Ứng dụng quản lý lịch trình chính"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Personal Schedule Assistant - Trợ lý Lịch trình Cá nhân")
        self.root.geometry("1200x800")  # Tăng kích thước để chứa thêm cột
        
        self.nlp_processor = VietnameseNLPProcessor()
        self.db_manager = DatabaseManager()
        self.reminder_system = ReminderSystem(self.db_manager, self.show_reminder_popup)
        
        self.setup_gui()
        self.reminder_system.start()
        self.load_events()
    
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        title_label = ttk.Label(main_frame, text="TRỢ LÝ LỊCH TRÌNH CÁ NHÂN", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        input_label = ttk.Label(main_frame, text="Nhập yêu cầu bằng tiếng Việt:")
        input_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        self.input_text = tk.Text(main_frame, height=3, width=80)
        self.input_text.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.add_button = ttk.Button(main_frame, text="Thêm sự kiện", command=self.add_event_from_text)
        self.add_button.grid(row=2, column=0, pady=(0, 10))
        
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        search_label = ttk.Label(search_frame, text="Tìm kiếm:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.search_button = ttk.Button(search_frame, text="Tìm", command=self.search_events)
        self.search_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Cập nhật columns để thêm "Thời gian kết thúc"
        columns = ("ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc nhở")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
        
        # Định nghĩa kích thước các cột
        column_widths = {
            "ID": 50,
            "Sự kiện": 200,
            "Thời gian bắt đầu": 150,
            "Thời gian kết thúc": 150,
            "Địa điểm": 150,
            "Nhắc nhở": 100
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))
        
        self.tree.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=3, column=3, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.edit_button = ttk.Button(button_frame, text="Sửa", command=self.edit_event)
        self.edit_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = ttk.Button(button_frame, text="Xóa", command=self.delete_event)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.refresh_button = ttk.Button(button_frame, text="Làm mới", command=self.load_events)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(button_frame, text="Xuất JSON", command=self.export_events)
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Nút test NLP
        self.test_button = ttk.Button(button_frame, text="Test NLP", command=self.test_nlp)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=5, column=0, columnspan=3, sticky=tk.W)
    
    def test_nlp(self):
        """Test chức năng NLP với câu mẫu"""
        test_cases = [
            # 5 test case gốc (có lời nhắc)
            "nhắc tôi họp nhóm lúc 10 giờ sáng mai ở phòng 302, nhắc trước 15 phút",
            "nhac toi hop nhom luc 10 gio 30 sáng mai va ket thuc luc 12h o phong 302, nhac truoc 15 phut",
            "nhắc tôi họp công ty lúc 10:30 thứ 2 tuần tới tại tầng trệt , nhắc trước 20 p",
            "nhắc tôi họp công ty lúc 10:30 chủ nhật tuần sau tại tầng trệt , nhắc trước 20 p",
            "nhắc tôi họp công ty lúc 9:30 cuối tuần tại tầng 5, nhắc trước 20 phút",
            
            # 30 test case mới (một số có lời nhắc, một số không dấu)
            "Nhắc tôi họp lúc 8h30 sáng mai tại văn phòng, nhắc trước 30 phút",
            "Nhắc tôi gọi điện cho khách hàng lúc 15 giờ ngày mai.",
            "Nhac toi hop luc 10:00 thu Ba tuan sau, nhac truoc 1 gio",
            "Nhắc tôi đi tập thể dục lúc 6 giờ sáng thứ Tư này.",
            "Nhac toi nop bao cao luc 17h thu Sau, nhac truoc 2 gio", 
            "Nhắc tôi họp nhóm lúc 14h30 chiều mai.",
            "Nhắc tôi đón con lúc 11:45 trưa mai, nhắc trước 15 phút",
            "Gap doi tac luc 9 gio sang thu Hai toi", 
            "Nhắc tôi họp công ty lúc 13:00 ngày kia, nhắc trước 45 phút",
            "Di kham benh luc 8 gio 15 phut sang thu Bay", 
            "Nhắc tôi họp online lúc 20:00 tối nay, nhắc trước 10 phút",
            "Nhắc tôi học bài lúc 19h30 tối thứ Năm.",
            "Hop luc 10 gio sang cuoi tuan, nhac truoc 30 phut", 
            "Nhắc tôi gửi email lúc 16h45 chiều thứ Tư.",
            "Nhắc tôi họp lúc 9:00 sáng chủ nhật tuần này, nhắc trước 1 giờ",
            "Di sieu thi luc 10 gio 30 sang thu Bay", 
            "Nhắc tôi họp lúc 11h trưa mai, nhắc trước 20 phút",
            "Goi cho sep luc 15:30 chieu thu Sau", 
            "Nhắc tôi họp tổng kết lúc 14 giờ ngày mai, nhắc trước 1 giờ",
            "Dam cuoi luc 17:00 thu Bay tuan sau", 
            "Nhắc tôi họp lúc 8 giờ sáng thứ Hai tuần tới, nhắc trước 25 phút",
            "Gap ban luc 18h30 toi thu Tu", 
            "Nhắc tôi họp lúc 7:45 sáng mai, nhắc trước 15 phút",
            "Nop bai luc 23:59 toi chu nhat", 
            "Nhắc tôi họp lúc 12:00 trưa thứ Năm, nhắc trước 30 phút",
            "Don nha luc 9 gio sang thu Bay", 
            "Nhắc tôi họp lúc 10h30 sáng thứ Hai tuần này, nhắc trước 40 phút",
            "Goi dien thoai luc 21:00 toi mai", 
            "Nhắc tôi họp lúc 16 giờ chiều cuối tuần, nhắc trước 1 giờ",
            "Di may bay luc 6:00 sang thu Sau tuan toi" 
        ]
        
        print("\n" + "="*60)
        print("KẾT QUẢ TEST NLP")
        print("="*60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- TEST {i} ---")
            print(f"Input: {test_case}")
            result = self.nlp_processor.process_text(test_case)
            if "error" not in result:
                start_time = datetime.fromisoformat(result['start_time'])
                end_time = datetime.fromisoformat(result['end_time']) if result['end_time'] else None
                
                print(f"✓ Sự kiện: {result['event']}")
                print(f"✓ Thời gian bắt đầu: {start_time.strftime('%H:%M %d/%m/%Y')}")
                if end_time:
                    print(f"✓ Thời gian kết thúc: {end_time.strftime('%H:%M %d/%m/%Y')}")
                else:
                    print(f"✓ Thời gian kết thúc: Không có")
                print(f"✓ Địa điểm: {result['location']}")
                print(f"✓ Nhắc nhở: trước {result['reminder_minutes']} phút")
            else:
                print(f"✗ Lỗi: {result['error']}")
        
        print("\n" + "="*60)
    
    def add_event_from_text(self):
        text = self.input_text.get("1.0", tk.END).strip()
        
        if not text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập yêu cầu!")
            return
        
        self.status_var.set("Đang xử lý tiếng Việt...")
        self.root.update()
        
        result = self.nlp_processor.process_text(text)
        
        if "error" in result:
            messagebox.showerror("Lỗi", result["error"])
            self.status_var.set("Lỗi xử lý")
            return
        
        # Hiển thị kết quả chi tiết
        start_time = datetime.fromisoformat(result['start_time'])
        end_time = datetime.fromisoformat(result['end_time']) if result['end_time'] else None
        
        confirmation_msg = f"""
Kết quả trích xuất:
- Sự kiện: {result['event']}
- Thời gian bắt đầu: {start_time.strftime('%H:%M %d/%m/%Y')}
- Thời gian kết thúc: {end_time.strftime('%H:%M %d/%m/%Y') if end_time else 'Không có'}
- Địa điểm: {result['location']}
- Nhắc nhở: trước {result['reminder_minutes']} phút

Bạn có muốn thêm sự kiện này?
        """
        
        if messagebox.askyesno("Xác nhận", confirmation_msg):
            event_id = self.db_manager.add_event(result)
            self.status_var.set(f"Đã thêm sự kiện #{event_id}")
            self.input_text.delete("1.0", tk.END)
            self.load_events()
        else:
            self.status_var.set("Đã hủy thêm sự kiện")
    
    def load_events(self, events=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if events is None:
            events = self.db_manager.get_events()
        
        for event in events:
            event_id, event_name, start_time_str, end_time_str, location, reminder_minutes, created_at = event
            start_time = datetime.fromisoformat(start_time_str)
            
            # Xử lý thời gian kết thúc
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str)
                end_time_display = end_time.strftime('%H:%M %d/%m/%Y')
            else:
                end_time_display = "Không có"
            
            self.tree.insert("", tk.END, values=(
                event_id,
                event_name,
                start_time.strftime('%H:%M %d/%m/%Y'),
                end_time_display,
                location,
                f"{reminder_minutes} phút" if reminder_minutes > 0 else "Không"
            ))
    
    def search_events(self):
        keyword = self.search_entry.get().strip()
        
        if not keyword:
            self.load_events()
            return
        
        events = self.db_manager.search_events(keyword)
        self.load_events(events)
        self.status_var.set(f"Tìm thấy {len(events)} kết quả cho '{keyword}'")
    
    def edit_event(self):
        selected_item = self.tree.selection()
        
        if not selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn sự kiện để sửa!")
            return
        
        item = selected_item[0]
        event_id = self.tree.item(item, "values")[0]
        
        events = self.db_manager.get_events()
        current_event = None
        
        for event in events:
            if str(event[0]) == event_id:
                current_event = {
                    "event": event[1],
                    "start_time": event[2],
                    "end_time": event[3],
                    "location": event[4],
                    "reminder_minutes": event[5]
                }
                break
        
        if not current_event:
            messagebox.showerror("Lỗi", "Không tìm thấy sự kiện!")
            return
        
        edit_dialog = EditEventDialog(self.root, current_event)
        self.root.wait_window(edit_dialog.dialog)
        
        if edit_dialog.result:
            self.db_manager.update_event(event_id, edit_dialog.result)
            self.status_var.set(f"Đã cập nhật sự kiện #{event_id}")
            self.load_events()
    
    def delete_event(self):
        selected_item = self.tree.selection()
        
        if not selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn sự kiện để xóa!")
            return
        
        item = selected_item[0]
        event_id = self.tree.item(item, "values")[0]
        event_name = self.tree.item(item, "values")[1]
        
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa sự kiện '{event_name}'?"):
            self.db_manager.delete_event(event_id)
            self.status_var.set(f"Đã xóa sự kiện #{event_id}")
            self.load_events()
    
    def export_events(self):
        events = self.db_manager.get_events()
        
        export_data = []
        for event in events:
            event_id, event_name, start_time_str, end_time_str, location, reminder_minutes, created_at = event
            
            export_data.append({
                "event": event_name,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "location": location,
                "reminder_minutes": reminder_minutes
            })
        
        filename = f"schedule_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.status_var.set(f"Đã xuất {len(export_data)} sự kiện ra {filename}")
        messagebox.showinfo("Thành công", f"Đã xuất dữ liệu ra file {filename}")
    
    def show_reminder_popup(self, message):
        messagebox.showinfo("NHẮC NHỞ SỰ KIỆN", message)

class EditEventDialog:
    def __init__(self, parent, event_data):
        self.parent = parent
        self.event_data = event_data
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Chỉnh sửa sự kiện")
        self.dialog.geometry("500x400")  # Tăng kích thước để chứa thêm trường
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
    
    def setup_dialog(self):
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tên sự kiện
        ttk.Label(main_frame, text="Tên sự kiện:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.event_entry = ttk.Entry(main_frame, width=40)
        self.event_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.event_entry.insert(0, self.event_data["event"])
        
        # Thời gian bắt đầu
        ttk.Label(main_frame, text="Thời gian bắt đầu:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.start_time_entry = ttk.Entry(main_frame, width=40)
        self.start_time_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        start_time = datetime.fromisoformat(self.event_data["start_time"])
        self.start_time_entry.insert(0, start_time.strftime('%Y-%m-%d %H:%M'))
        
        # Thời gian kết thúc (MỚI)
        ttk.Label(main_frame, text="Thời gian kết thúc:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.end_time_entry = ttk.Entry(main_frame, width=40)
        self.end_time_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        if self.event_data["end_time"]:
            end_time = datetime.fromisoformat(self.event_data["end_time"])
            self.end_time_entry.insert(0, end_time.strftime('%Y-%m-%d %H:%M'))
        else:
            self.end_time_entry.insert(0, "")
        
        # Địa điểm
        ttk.Label(main_frame, text="Địa điểm:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.location_entry = ttk.Entry(main_frame, width=40)
        self.location_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        self.location_entry.insert(0, self.event_data["location"])
        
        # Nhắc nhở
        ttk.Label(main_frame, text="Nhắc nhở (phút):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.reminder_entry = ttk.Entry(main_frame, width=40)
        self.reminder_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        self.reminder_entry.insert(0, str(self.event_data["reminder_minutes"]))
        
        # Nút
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Lưu", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
    
    def save(self):
        try:
            self.result = {
                "event": self.event_entry.get(),
                "start_time": datetime.strptime(self.start_time_entry.get(), '%Y-%m-%d %H:%M').isoformat(),
                "end_time": datetime.strptime(self.end_time_entry.get(), '%Y-%m-%d %H:%M').isoformat() if self.end_time_entry.get() else None,
                "location": self.location_entry.get(),
                "reminder_minutes": int(self.reminder_entry.get())
            }
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Lỗi", "Định dạng thời gian không hợp lệ! Sử dụng YYYY-MM-DD HH:MM\nThời gian kết thúc có thể để trống")
    
    def cancel(self):
        self.dialog.destroy()

def main():
    root = tk.Tk()
    app = ScheduleApp(root)
    
    def on_closing():
        app.reminder_system.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
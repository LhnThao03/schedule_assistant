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
                time.sleep(60)

class ScheduleApp:
    """Ứng dụng quản lý lịch trình chính với giao diện hiện đại"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Personal Schedule Assistant ✨")
        self.root.geometry("1400x900")

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        window_width = 1400
        window_height = 900
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Thiết lập màu sắc
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'accent': '#e74c3c',
            'success': '#2ecc71',
            'light': '#ecf0f1',
            'dark': '#34495e',
            'calendar_bg': '#ffffff',
            'event_bg': '#3498db',
            'today_bg': '#f1c40f'
        }
        
        # Cài đặt style
        self.setup_styles()
        
        self.nlp_processor = VietnameseNLPProcessor()
        self.db_manager = DatabaseManager()
        self.reminder_system = ReminderSystem(self.db_manager, self.show_reminder_popup)
        
        self.setup_gui()
        self.reminder_system.start()
        self.load_events()
        self.update_calendar()
    
    def setup_styles(self):
        """Cấu hình styles cho giao diện"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cấu hình các style tùy chỉnh
        style.configure('Primary.TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       padding=6,
                       background=self.colors['secondary'])
        style.configure('Secondary.TButton',
                       font=('Segoe UI', 10),
                       padding=5)
        style.configure('Title.TLabel',
                       font=('Segoe UI', 18, 'bold'),
                       foreground=self.colors['primary'])
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 12, 'bold'),
                       foreground=self.colors['dark'])
        style.configure('Card.TLabelframe',
                       borderwidth=2,
                       relief='groove',
                       padding=10)
        style.configure('Card.TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       foreground=self.colors['primary'])
    
    def setup_gui(self):
        # Tạo main container
        main_container = ttk.Frame(self.root, padding="0")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # ==================== HEADER ====================
        header_frame = tk.Frame(main_container, bg=self.colors['primary'], height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Logo và tiêu đề
        logo_frame = tk.Frame(header_frame, bg=self.colors['primary'])
        logo_frame.pack(side=tk.LEFT, padx=20)
        
        title_label = tk.Label(logo_frame, 
                              text="📅 Personal Schedule Assistant", 
                              font=('Segoe UI', 20, 'bold'),
                              bg=self.colors['primary'],
                              fg='white')
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(logo_frame,
                                 text="Trợ lý lịch trình thông minh",
                                 font=('Segoe UI', 11),
                                 bg=self.colors['primary'],
                                 fg=self.colors['light'])
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status label trên header
        self.status_var = tk.StringVar()
        self.status_var.set("🟢 Sẵn sàng")
        status_label = tk.Label(header_frame,
                               textvariable=self.status_var,
                               font=('Segoe UI', 10),
                               bg=self.colors['primary'],
                               fg='white')
        status_label.pack(side=tk.RIGHT, padx=20)
        
        # ==================== MAIN CONTENT ====================
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # ===== LEFT PANEL: Nhập liệu và Lịch =====
        left_panel = ttk.Frame(content_frame, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # --- Nhập sự kiện ---
        input_card = ttk.LabelFrame(left_panel, text="➕ Thêm sự kiện mới", padding=15)
        input_card.pack(fill=tk.X, pady=(0, 15))
        
        # Hướng dẫn
        guide_label = ttk.Label(input_card,
                               text="Nhập yêu cầu bằng tiếng Việt tự nhiên:",
                               font=('Segoe UI', 10))
        guide_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Ví dụ
        example_text = "Ví dụ: 'họp lúc 10h sáng mai tại phòng 302, nhắc trước 15 phút'"
        example_label = ttk.Label(input_card,
                                 text=example_text,
                                 font=('Segoe UI', 9, 'italic'),
                                 foreground='#666')
        example_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Ô nhập văn bản với scrollbar
        input_container = ttk.Frame(input_card)
        input_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.input_text = tk.Text(input_container,
                                 height=4,
                                 font=('Segoe UI', 10),
                                 wrap=tk.WORD,
                                 bg='white',
                                 relief=tk.SOLID,
                                 borderwidth=1)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_scrollbar = ttk.Scrollbar(input_container, command=self.input_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_text.configure(yscrollcommand=text_scrollbar.set)
        
        # Nút Thêm sự kiện
        button_container = ttk.Frame(input_card)
        button_container.pack(fill=tk.X)
        
        self.add_button = ttk.Button(button_container,
                                    text="🎯 Thêm sự kiện",
                                    command=self.add_event_from_text,
                                    style='Primary.TButton')
        self.add_button.pack(side=tk.LEFT, pady=(5, 0))
        
        # Nút Test NLP
        # self.test_button = ttk.Button(button_container,
        #                              text="🧪 Test NLP",
        #                              command=self.test_nlp,
        #                              style='Secondary.TButton')
        # self.test_button.pack(side=tk.LEFT, padx=(10, 0), pady=(5, 0))
        
        # --- Tìm kiếm ---
        search_card = ttk.LabelFrame(left_panel, text="🔍 Tìm kiếm sự kiện", padding=15)
        search_card.pack(fill=tk.X, pady=(0, 15))
        
        search_frame = ttk.Frame(search_card)
        search_frame.pack(fill=tk.X)
        
        self.search_entry = ttk.Entry(search_frame,
                                     font=('Segoe UI', 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.search_button = ttk.Button(search_frame,
                                       text="Tìm",
                                       command=self.search_events,
                                       style='Primary.TButton')
        self.search_button.pack(side=tk.RIGHT)
        
        # --- Lịch sự kiện ---
        calendar_card = ttk.LabelFrame(left_panel, text="📅 Lịch sự kiện (7 ngày tới)", padding=15)
        calendar_card.pack(fill=tk.BOTH, expand=True)
        
        # Container cho calendar với scrollbar
        calendar_container = ttk.Frame(calendar_card)
        calendar_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas cho calendar
        self.calendar_canvas = tk.Canvas(calendar_container,
                                        bg='white',
                                        highlightthickness=0)
        scrollbar = ttk.Scrollbar(calendar_container,
                                 orient="horizontal",
                                 command=self.calendar_canvas.xview)
        
        self.calendar_canvas.configure(xscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.calendar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame bên trong canvas
        self.calendar_inner_frame = ttk.Frame(self.calendar_canvas)
        self.calendar_window = self.calendar_canvas.create_window((0, 0),
                                                                 window=self.calendar_inner_frame,
                                                                 anchor="nw")
        
        # ===== RIGHT PANEL: Danh sách sự kiện =====
        right_panel = ttk.Frame(content_frame, width=800)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))
        
        # --- Danh sách sự kiện ---
        list_card = ttk.LabelFrame(right_panel, text="📋 Danh sách sự kiện", padding=15)
        list_card.pack(fill=tk.BOTH, expand=True)
        
        # Container cho treeview
        tree_container = ttk.Frame(list_card)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Tạo Treeview với style
        style = ttk.Style()
        style.configure("Treeview",
                       font=('Segoe UI', 10),
                       rowheight=25)
        style.configure("Treeview.Heading",
                       font=('Segoe UI', 11, 'bold'),
                       background=self.colors['light'])
        
        columns = ("ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc nhở")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=15)
        
        # Định nghĩa kích thước các cột
        column_widths = {
            "ID": 50,
            "Sự kiện": 150,
            "Thời gian bắt đầu": 160,
            "Thời gian kết thúc": 160,
            "Địa điểm": 150,
            "Nhắc nhở": 100
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))
        
        # Thêm scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        # --- Panel nút chức năng ---
        button_panel = ttk.Frame(right_panel)
        button_panel.pack(fill=tk.X, pady=(15, 0))
        
        # Các nút chức năng
        buttons = [
            ("✏️ Sửa", self.edit_event, 'Secondary.TButton'),
            ("🗑️ Xóa", self.delete_event, 'Secondary.TButton'),
            ("📤 Xuất JSON", self.export_events, 'Secondary.TButton'),
            ("🔄 Làm mới", self.refresh_all, 'Primary.TButton'),
        ]
        
        for text, command, style_name in buttons:
            btn = ttk.Button(button_panel,
                            text=text,
                            command=command,
                            style=style_name)
            btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # ==================== FOOTER ====================
        footer_frame = tk.Frame(main_container, bg=self.colors['light'], height=30)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        footer_label = tk.Label(footer_frame,
                               text="© 2024 Personal Schedule Assistant | Trợ lý lịch trình thông minh",
                               font=('Segoe UI', 9),
                               bg=self.colors['light'],
                               fg=self.colors['dark'])
        footer_label.pack(pady=5)
        
        # ==================== BIND EVENTS ====================
        self.calendar_inner_frame.bind("<Configure>", self.on_calendar_configure)
        self.calendar_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Bind Enter key cho tìm kiếm
        self.search_entry.bind('<Return>', lambda e: self.search_events())
    
    def on_calendar_configure(self, event):
        """Cập nhật scrollregion khi calendar thay đổi kích thước"""
        self.calendar_canvas.configure(scrollregion=self.calendar_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """Cập nhật kích thước của inner frame khi canvas thay đổi"""
        self.calendar_canvas.itemconfig(self.calendar_window, width=event.width)
    
    def update_calendar(self):
        """Cập nhật bảng lịch với thiết kế đẹp"""
        # Xóa các widget cũ
        for widget in self.calendar_inner_frame.winfo_children():
            widget.destroy()
        
        # Lấy ngày hiện tại
        today = datetime.now()
        
        # Tạo mảng 7 ngày tới
        days = []
        for i in range(7):
            current_day = today + timedelta(days=i)
            days.append(current_day)
        
        # Tạo header cho calendar
        for i, day in enumerate(days):
            is_today = (day.date() == today.date())
            
            # Tạo frame cho mỗi ngày
            day_frame = tk.Frame(self.calendar_inner_frame,
                                bg='#f8f9fa' if not is_today else '#fff3cd',
                                relief=tk.RAISED,
                                borderwidth=1)
            day_frame.grid(row=0, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
            
            # Header ngày
            header_bg = '#e9ecef' if not is_today else '#ffc107'
            header_frame = tk.Frame(day_frame, bg=header_bg, height=44)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            # Ngày và thứ
            day_label = tk.Label(header_frame,
                                text=day.strftime("%d\n%b"),
                                font=('Segoe UI', 11, 'bold'),
                                bg=header_bg)
            day_label.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Thứ trong tuần
            weekday_label = tk.Label(header_frame,
                                    text=day.strftime("(%A)"),
                                    font=('Segoe UI', 9),
                                    bg=header_bg,
                                    fg='#666')
            weekday_label.pack(side=tk.LEFT, pady=5)
            
            # Đánh dấu hôm nay
            if is_today:
                today_label = tk.Label(header_frame,
                                      text="NOW",
                                      font=('Segoe UI', 8, 'bold'),
                                      bg='#dc3545',
                                      fg='white')
                today_label.pack(side=tk.RIGHT, padx=5, pady=2)
            
            # Nội dung sự kiện
            content_frame = tk.Frame(day_frame, bg='white')
            content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Lấy tất cả sự kiện
        events = self.db_manager.get_events()
        
        # Nhóm sự kiện theo ngày
        for i, day in enumerate(days):
            # Lấy content_frame cho ngày này
            day_widget = self.calendar_inner_frame.grid_slaves(row=0, column=i)[0]
            content_frame = day_widget.winfo_children()[1]  # Lấy content_frame
            
            # Đếm sự kiện cho ngày này
            day_events = []
            for event in events:
                event_id, event_name, start_time_str, end_time_str, location, reminder_minutes, created_at = event
                start_time = datetime.fromisoformat(start_time_str)
                
                if start_time.date() == day.date():
                    day_events.append((event_id, event_name, start_time, location))
            
            # Sắp xếp sự kiện theo thời gian
            day_events.sort(key=lambda x: x[2])
            
            # Hiển thị các sự kiện
            for idx, (event_id, event_name, start_time, location) in enumerate(day_events[:5]):  # Tối đa 5 sự kiện
                event_color = self.get_event_color(idx)
                
                event_frame = tk.Frame(content_frame,
                                      bg=event_color,
                                      relief=tk.RAISED,
                                      borderwidth=1)
                event_frame.pack(fill=tk.X, pady=2)
                
                # Thời gian
                time_label = tk.Label(event_frame,
                                     text=start_time.strftime("%H:%M"),
                                     font=('Segoe UI', 9, 'bold'),
                                     bg=event_color,
                                     width=6)
                time_label.pack(side=tk.LEFT, padx=5, pady=2)
                
                # Tên sự kiện
                name_label = tk.Label(event_frame,
                                     text=event_name[:20] + ('...' if len(event_name) > 20 else ''),
                                     font=('Segoe UI', 9),
                                     bg=event_color,
                                     anchor='w')
                name_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
                
                # Bind click event
                event_frame.bind("<Button-1>", lambda e, ev_id=event_id: self.highlight_event(ev_id))
                time_label.bind("<Button-1>", lambda e, ev_id=event_id: self.highlight_event(ev_id))
                name_label.bind("<Button-1>", lambda e, ev_id=event_id: self.highlight_event(ev_id))
                
                # Tooltip
                tooltip_text = f"{event_name}\n⏰ {start_time.strftime('%H:%M')}\n📍 {location}"
                self.create_tooltip(event_frame, tooltip_text)
            
            # Nếu có nhiều hơn 5 sự kiện, hiển thị thông báo
            if len(day_events) > 5:
                more_label = tk.Label(content_frame,
                                     text=f"... và {len(day_events)-5} sự kiện khác",
                                     font=('Segoe UI', 8, 'italic'),
                                     fg='#666',
                                     bg='white')
                more_label.pack(pady=2)
        
        # Cấu hình grid
        for i in range(7):
            self.calendar_inner_frame.columnconfigure(i, weight=1)
    
    def get_event_color(self, index):
        """Lấy màu cho sự kiện dựa trên index"""
        colors = [
            '#3498db',  # Blue
            '#2ecc71',  # Green
            '#e74c3c',  # Red
            '#f39c12',  # Orange
            '#9b59b6',  # Purple
            '#1abc9c',  # Turquoise
            '#d35400',  # Pumpkin
        ]
        return colors[index % len(colors)]
    
    def create_tooltip(self, widget, text):
        """Tạo tooltip đẹp cho widget"""
        def show_tooltip(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Tạo tooltip window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            # Tạo tooltip content
            tooltip_frame = tk.Frame(self.tooltip,
                                    bg='#333',
                                    relief=tk.SOLID,
                                    borderwidth=1)
            tooltip_frame.pack()
            
            tooltip_label = tk.Label(tooltip_frame,
                                    text=text,
                                    font=('Segoe UI', 9),
                                    bg='#333',
                                    fg='white',
                                    padx=10,
                                    pady=5,
                                    justify=tk.LEFT)
            tooltip_label.pack()
        
        def hide_tooltip(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                delattr(self, 'tooltip')
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def highlight_event(self, event_id):
        """Highlight sự kiện trong danh sách"""
        for item in self.tree.get_children():
            if self.tree.item(item, "values")[0] == str(event_id):
                self.tree.selection_remove(self.tree.selection())
                self.tree.selection_set(item)
                self.tree.see(item)
                self.tree.focus(item)
                
                # Tạo tag highlight
                self.tree.tag_configure("highlight", background='#d4edda')
                self.tree.item(item, tags=("highlight",))
                
                self.root.after(2000, lambda: self.tree.item(item, tags=()))
                break
    
    def refresh_all(self):
        """Làm mới tất cả dữ liệu"""
        self.load_events()
        self.update_calendar()
        self.status_var.set("🔄 Đã làm mới dữ liệu")
    
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
    def __init__(self, parent, current_event):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sửa sự kiện")
        self.dialog.geometry("500x500")  # Kích thước cửa sổ
        
        # Đặt cửa sổ ở giữa màn hình
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        window_width = 500
        window_height = 500
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.dialog.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Ngăn không cho tương tác với cửa sổ chính
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.result = None
        self.setup_gui(current_event)
    
    def setup_gui(self, current_event):
        # Tạo main frame với padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        title_label = ttk.Label(main_frame, 
                            text="✏️ Sửa thông tin sự kiện",
                            font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Tên sự kiện
        ttk.Label(main_frame, text="Tên sự kiện:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self.event_var = tk.StringVar(value=current_event["event"])
        event_entry = ttk.Entry(main_frame, textvariable=self.event_var, width=50)
        event_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Thời gian bắt đầu
        ttk.Label(main_frame, text="Thời gian bắt đầu:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X, pady=(5, 15))
        
        # Parse thời gian từ chuỗi ISO
        start_time = datetime.fromisoformat(current_event["start_time"])
        
        # Ngày
        self.date_var = tk.StringVar(value=start_time.strftime("%d/%m/%Y"))
        date_entry = ttk.Entry(time_frame, textvariable=self.date_var, width=15)
        date_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Giờ
        self.hour_var = tk.StringVar(value=start_time.strftime("%H"))
        hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var, width=5)
        hour_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        
        # Phút
        self.minute_var = tk.StringVar(value=start_time.strftime("%M"))
        minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var, width=5)
        minute_spinbox.pack(side=tk.LEFT)
        
        # Thời gian kết thúc (luôn hiển thị, có thể để trống)
        ttk.Label(main_frame, text="Thời gian kết thúc (tùy chọn):", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(10, 0))
        
        end_time_frame = ttk.Frame(main_frame)
        end_time_frame.pack(fill=tk.X, pady=(5, 15))
        
        # Parse thời gian kết thúc nếu có
        if current_event["end_time"]:
            end_time = datetime.fromisoformat(current_event["end_time"])
            self.end_date_var = tk.StringVar(value=end_time.strftime("%d/%m/%Y"))
            self.end_hour_var = tk.StringVar(value=end_time.strftime("%H"))
            self.end_minute_var = tk.StringVar(value=end_time.strftime("%M"))
        else:
            self.end_date_var = tk.StringVar(value="")
            self.end_hour_var = tk.StringVar(value="")
            self.end_minute_var = tk.StringVar(value="")
        
        end_date_entry = ttk.Entry(end_time_frame, textvariable=self.end_date_var, width=15)
        end_date_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        end_hour_spinbox = ttk.Spinbox(end_time_frame, from_=0, to=23, textvariable=self.end_hour_var, width=5)
        end_hour_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(end_time_frame, text=":").pack(side=tk.LEFT)
        
        end_minute_spinbox = ttk.Spinbox(end_time_frame, from_=0, to=59, textvariable=self.end_minute_var, width=5)
        end_minute_spinbox.pack(side=tk.LEFT)
        
        # Địa điểm
        ttk.Label(main_frame, text="Địa điểm:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self.location_var = tk.StringVar(value=current_event["location"])
        location_entry = ttk.Entry(main_frame, textvariable=self.location_var, width=50)
        location_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Nhắc nhở
        ttk.Label(main_frame, text="Nhắc nhở (phút):", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self.reminder_var = tk.StringVar(value=str(current_event["reminder_minutes"]))
        reminder_spinbox = ttk.Spinbox(main_frame, from_=0, to=1440, textvariable=self.reminder_var, width=10)
        reminder_spinbox.pack(anchor=tk.W, pady=(5, 20))
        
        # Nút hành động
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="Lưu", command=self.save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Hủy", command=self.cancel).pack(side=tk.RIGHT)
    
    def save(self):
        try:
            # Parse ngày bắt đầu
            day, month, year = map(int, self.date_var.get().split('/'))
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            start_time = datetime(year, month, day, hour, minute)
            start_time_str = start_time.isoformat()
            
            # Parse ngày kết thúc (nếu có dữ liệu)
            end_time_str = None
            if self.end_date_var.get() and self.end_hour_var.get() and self.end_minute_var.get():
                try:
                    end_day, end_month, end_year = map(int, self.end_date_var.get().split('/'))
                    end_hour = int(self.end_hour_var.get())
                    end_minute = int(self.end_minute_var.get())
                    
                    end_time = datetime(end_year, end_month, end_day, end_hour, end_minute)
                    end_time_str = end_time.isoformat()
                except:
                    # Nếu có lỗi khi parse thời gian kết thúc, bỏ qua và để None
                    pass
            
            self.result = {
                "event": self.event_var.get(),
                "start_time": start_time_str,
                "end_time": end_time_str,
                "location": self.location_var.get(),
                "reminder_minutes": int(self.reminder_var.get())
            }
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Dữ liệu không hợp lệ: {str(e)}")
    
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
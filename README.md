# 📅 Personal Schedule Assistant - Trợ lý Lịch trình Cá nhân

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Complete-success.svg)]()

**Một ứng dụng quản lý lịch trình thông minh với khả năng xử lý ngôn ngữ tự nhiên tiếng Việt**

---

## 📋 Mục lục
- [🎯 Giới thiệu](#-giới-thiệu)
- [✨ Tính năng chính](#-tính-năng-chính)
- [🛠️ Cài đặt và Sử dụng](#️-cài-đặt-và-sử-dụng)
- [📁 Cấu trúc dự án](#-cấu-trúc-dự-án)
- [🧠 Xử lý NLP tiếng Việt](#-xử-lý-nlp-tiếng-việt)
- [📚 Hướng dẫn sử dụng](#-hướng-dẫn-sử-dụng)
- [🔧 Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [📄 Tài liệu tham khảo](#-tài-liệu-tham-khảo)

---
## 🎯 Giới thiệu

**Personal Schedule Assistant** là ứng dụng quản lý lịch trình cá nhân thông minh được phát triển bằng Python, tích hợp khả năng xử lý ngôn ngữ tự nhiên (NLP) tiếng Việt. Ứng dụng cho phép người dùng thêm sự kiện bằng cách nhập câu tiếng Việt tự nhiên, tự động trích xuất thông tin và quản lý lịch trình một cách hiệu quả.

### 📌 Mục tiêu dự án
- Xây dựng ứng dụng quản lý lịch trình thông minh
- Tích hợp xử lý NLP tiếng Việt
- Hỗ trợ đa dạng định dạng thời gian
- Xuất/nhập dữ liệu linh hoạt
- Giao diện thân thiện, dễ sử dụng

---

## ✨ Tính năng chính

### 🔤 Xử lý ngôn ngữ tự nhiên tiếng Việt
- Hiểu và xử lý câu tiếng Việt tự nhiên
- Hỗ trợ cả văn bản có dấu và không dấu
- Trích xuất tự động: sự kiện, thời gian, địa điểm, nhắc nhở
- Độ chính xác ≥80% trên 30 test case

### 🕒 Hỗ trợ đa dạng định dạng thời gian
- **Giờ:** `10h`, `10 giờ`, `10:30`, `10h30`
- **Ngày:** `sáng mai`, `chiều nay`, `tối nay`, `ngày kia`
- **Thứ:** `thứ Hai`, `thứ 2`, `thứ Hai tới`, `thứ 2 tuần sau`
- **Tuần:** `tuần này`, `tuần sau`, `tuần tới`, `cuối tuần`

### 🖥️ Giao diện người dùng
- **Ô nhập văn bản tự do** với hỗ trợ tiếng Việt
- **Bảng lịch 7 ngày** hiển thị trực quan
- **Danh sách sự kiện** với đầy đủ thông tin
- **Tìm kiếm** sự kiện nhanh chóng
- **Nhắc nhở tự động** qua popup

### 💾 Quản lý dữ liệu
- **Lưu trữ cục bộ** với SQLite
- **Xuất dữ liệu:** JSON và iCalendar (.ics)
- **CRUD đầy đủ:** Thêm, Sửa, Xóa, Tìm kiếm
- **Nhắc nhở thông minh** chạy nền

### 🔄 Tích hợp và chia sẻ
- **Export iCalendar** tương thích với Google Calendar, Outlook, Apple Calendar
- **Backup/Restore** dữ liệu bằng JSON
- **Chia sẻ lịch** dễ dàng qua file .ics

---

## 🛠️ Cài đặt và Sử dụng

### 📦 Yêu cầu hệ thống
- Python 3.8 hoặc cao hơn
- Hệ điều hành: Windows, macOS, Linux

### 🔧 Cài đặt

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/personal-schedule-assistant.git
cd personal-schedule-assistant
```

2. **Cài đặt thư viện và chạy ứng dụng**
```bash
pip install underthesea
python main.py
```

## 📁 Cấu trúc dự án
```bash
personal-schedule-assistant/
├── README.md                    # Tài liệu hướng dẫn
├── main.py                      # File code chính
├── requirements.txt             # Danh sách thư viện
├── schedule.db                  # Database (tự động tạo)
├── schedule_export_*.json       # File export JSON (tự động tạo)
└── schedule_export_*.ics        # File export iCalendar (tự động tạo)
```

## 🧠 Xử lý NLP tiếng Việt
**Các mẫu câu hỗ trợ**
```bash
# Thời gian
"họp lúc 10h sáng mai"
"họp lúc 10 giờ sáng thứ Hai"
"họp lúc 10:30 chiều thứ 3 tuần tới"

# Địa điểm
"tại phòng 302"
"ở tầng 5"
"o phong hop"  # không dấu

# Nhắc nhở
"nhắc trước 15 phút"
"nhắc trước 2 giờ"
"nhac truoc 30 phut"  # không dấu
```
## 📚 Hướng dẫn sử dụng
```bash
1. Nhập câu tiếng Việt vào ô "Nhập yêu cầu"
   Ví dụ: "Nhắc tôi họp lúc 10h sáng mai tại phòng 302, nhắc trước 15 phút"

2. Nhấn nút "🎯 Thêm sự kiện"

3. Xác nhận thông tin trích xuất:
   - Sự kiện: Họp
   - Thời gian: 10:00 ngày mai
   - Địa điểm: phòng 302
   - Nhắc nhở: 15 phút trước

4. Nhấn "Yes" để thêm vào lịch
```

## 🔧 Kiến trúc hệ thống
```bash
1. Chuẩn hóa văn bản
   ↓
2. Tách từ với Underthesea
   ↓
3. Trích xuất thông tin:
   - Tên sự kiện
   - Thời gian bắt đầu/kết thúc
   - Địa điểm
   - Thời gian nhắc nhở
   ↓
4. Phân tích ngữ nghĩa
   ↓
5. Tạo đối tượng sự kiện
```

## 📄 Tài liệu tham khảo
1. [Underthesea Documentation](google.com/url?q=https://github.com/undertheseanlp/underthesea&sa=D&source=docs&ust=1764688387685398&usg=AOvVaw3_QcDC0Ub_h5k1zDGiqjrf)
2. [Python dateutil](https://dateutil.readthedocs.io/en/stable/)
3. [SQL Python Tutorial](https://docs.python.org/3/library/sqlite3.html)
4. [Tkinter](https://docs.python.org/3/library/tkinter.html)
5. [SQLite3](https://docs.python.org/3/library/sqlite3.html)
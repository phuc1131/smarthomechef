# WinMart Product Crawler

Công cụ crawl dữ liệu sản phẩm từ WinMart API và import vào database.

## Giới thiệu

Script này crawl dữ liệu sản phẩm từ WinMart theo các danh mục (Rau, Sữa, Thịt, v.v.) và lưu vào database để sử dụng cho hệ thống AI.

### Dữ liệu được crawl

- Tên sản phẩm
- Giá bán
- Đơn vị tính
- Thông tin dinh dưỡng
- Danh mục sản phẩm
- URL sản phẩm

### Các bảng dữ liệu

1. **Ingredients** (Django model): Tên nguyên liệu
2. **Food** (Django model): Thông tin dinh dưỡng
3. **ingredient_nutrition** (nếu dùng raw SQL): Dinh dưỡng chi tiết
4. **ingredient_prices** (nếu dùng raw SQL): Lịch sử giá

## Cách sử dụng

### Cách 1: Django Management Command (Recommended)

#### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

Yêu cầu:
- beautifulsoup4>=4.12.0
- requests>=2.32.0
- psycopg2-binary (đã có)

#### 2. Chạy crawl command

**Crawl tất cả danh mục:**
```bash
python manage.py crawl_winmart
```

**Crawl có giới hạn:**
```bash
# Crawl chỉ 3 danh mục đầu tiên
python manage.py crawl_winmart --limit-categories 3

# Crawl tối đa 50 sản phẩm trên mỗi danh mục
python manage.py crawl_winmart --limit-items 50

# Kết hợp cả hai
python manage.py crawl_winmart --limit-categories 2 --limit-items 30
```

**Hiển thị tiến trình:**
```bash
# Với verbose output
python manage.py crawl_winmart --verbosity 2
```

#### 3. Kiểm tra dữ liệu đã import

```bash
python manage.py shell
>>> from apps.nutrition.models import Ingredient, Food
>>> Ingredient.objects.count()  # Số ingredient
>>> Food.objects.filter(category='Rau Lá').count()  # Sản phẩm theo danh mục
```

### Cách 2: Chỉ dùng Django management command

Dự án đã tích hợp trực tiếp crawl WinMart vào Django, nên không cần dùng file SQL hoặc script riêng.

Bạn chỉ cần chạy:

```bash
python manage.py crawl_winmart
```

Hoặc chạy theo lịch tự động 12 tiếng 1 lần (00:00 và 12:00 mỗi ngày):

```bash
python manage.py crawl_winmart --schedule
```

Hoặc dùng giới hạn thử nghiệm:

```bash
python manage.py crawl_winmart --limit-categories 2 --limit-items 50
```

## Database Configuration

Đảm bảo `.env` có các biến:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=smart-chef
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

## Danh mục sản phẩm được crawl

1. **Rau, Quả**
   - Rau Lá
   - Củ, Quả
   - Trái cây tươi

2. **Sữa**
   - Sữa tươi
   - Sữa hạt, sữa đậu
   - Sữa bột
   - Bơ sữa, phô mai
   - Sữa đặc
   - Sữa chua, vàng sữa

3. **Thịt, Hải sản**
   - Thịt
   - Hải sản

4. **Bánh, Kẹo**
   - Bánh xốp, bánh quy
   - Kẹo, chocolate
   - Bánh snack
   - Hạt, trái cây sấy khô

5. **Thực phẩm khác**
   - Thực phẩm khô
   - Mì, thực phẩm ăn liền
   - Thực phẩm chế biến
   - Gia vị
   - Thực phẩm đông lạnh
   - Trứng, đậu hũ

## Troubleshooting

### Lỗi kết nối database

```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Giải pháp:**
- Kiểm tra PostgreSQL đang chạy: `pg_isready`
- Kiểm tra cấu hình .env
- Kiểm tra user/password đúng

### Lỗi timeout

```
requests.exceptions.ReadTimeout: Read timed out
```

**Giải pháp:**
- Tăng timeout trong code (mặc định 30s)
- Kiểm tra internet connection
- Thử crawl số lượng nhỏ trước

### Lỗi encoding Unicode

**Giải pháp:**
- Đảm bảo database sử dụng UTF-8 encoding
- Kiểm tra file .sql có `SET CLIENT_ENCODING = 'UTF8'`

## Performance Tips

1. **Crawl incremental:**
   ```bash
   python manage.py crawl_winmart --limit-categories 2
   ```

2. **Batch processing:**
   - Script tự động dùng `transaction.atomic()` cho performance tốt

3. **Kiểm tra trước khi import:**
   ```bash
   python manage.py crawl_winmart --limit-items 5  # Test 5 items trước
   ```

## API Reference

### WinMart API

```
GET https://api-crownx.winmart.vn/it/api/web/v3/item/category
  ?orderByDesc=true
  &pageNumber=1
  &pageSize=100
  &slug=rau-la--c01167
  &storeCode=1535
  &storeGroupCode=1998
```

**Response fields:**
- `name`: Tên sản phẩm
- `salePrice` / `price`: Giá bán
- `uom` / `uomName`: Đơn vị tính
- `longDescription`: Mô tả chi tiết
- `seoName`: URL-friendly name

## Chú ý

- Dữ liệu từ WinMart có thể thay đổi hàng ngày
- Giá bán được cập nhật mỗi lần crawl
- Script tự động skip duplicate (dùng `get_or_create`)
- Thông tin dinh dưỡng được parse từ HTML, có thể không chính xác 100%

## Hỗ trợ

Nếu có lỗi, kiểm tra:
1. Logs output từ command
2. Database connection
3. Internet connection
4. Format dữ liệu API WinMart (có thể thay đổi)

---

Created: 2024
Last Updated: May 3, 2026

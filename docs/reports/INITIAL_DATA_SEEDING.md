# 4.3. Thu thập & khởi tạo dữ liệu ban đầu cho hệ thống

Mục tiêu của tài liệu này là hướng dẫn cách chuẩn bị, tổ chức và nạp dữ liệu danh mục dùng chung và dữ liệu ban đầu (bootstrap data) cho hệ thống Smart Home Chef. Nội dung trình bày chi tiết: các loại dữ liệu cần khởi tạo, định dạng mẫu, quy trình nạp an toàn, kiểm tra, rollback và ví dụ cụ thể (danh sách chuyên ngành, lĩnh vực, tỉnh/thành phố,...).

---

## 1. Tổng quan và nguyên tắc

- Mục tiêu: đảm bảo hệ thống có dữ liệu tham chiếu đầy đủ để chạy các chức năng như tìm kiếm, lọc, import, cấu hình mặc định, và để AI có ngữ cảnh khởi đầu.
- Nguyên tắc:
  - Idempotent: các script/fixture có thể chạy nhiều lần mà không sinh bản ghi trùng.
  - Có thể lặp lại: dễ tái tạo trong môi trường dev/staging/production.
  - Có kiểm tra (validation) trước và sau khi nạp.
  - Có rollback / undo plan cho trường hợp lỗi.
  - Phiên bản hóa dữ liệu (kèm metadata: source, version, date, author).

## 2. Danh mục dữ liệu ưu tiên khởi tạo

Ưu tiên nạp những danh mục dùng chung được nhiều phần trong hệ thống:

1. Danh sách tỉnh/thành phố (provinces/cities)
2. Danh sách chuyên ngành / ngành nghề (specializations)
3. Danh mục lĩnh vực (domains/fields)
4. Loại bữa ăn (meal types): breakfast, lunch, dinner, snack, etc.
5. Đơn vị đo (units): gram, ml, serving, piece
6. Nhóm thực phẩm (food categories): fruit, vegetable, protein, dairy, grain, processed
7. Cấu hình mặc định (system settings): default language, currency, pagination size
8. Vai trò hệ thống (roles): user, admin, moderator
9. Mẫu dữ liệu demo (seed users, sample foods, sample recipes, sample meal plans)

> Gợi ý: danh sách chuyên ngành/lĩnh vực có thể là các chuyên ngành dinh dưỡng, y tế, thể hình, khoa học thực phẩm, công nghệ thực phẩm, v.v.

## 3. Định dạng dữ liệu mẫu và ví dụ

Khuyến nghị sử dụng CSV/JSON để lưu bản nguồn, kèm file manifest mô tả trường và mapping tới model Django.

3.1. Ví dụ: `provinces.csv`

| id | code | name_vi | name_en |
| --- | --- | --- | --- |
| 1 | AG | An Giang | An Giang |
| 2 | BRVT | Bà Rịa - Vũng Tàu | Ba Ria - Vung Tau |

3.2. Ví dụ: `specializations.csv`

| id | slug | name_vi | name_en | description |
| --- | --- | --- | --- | --- |
| 1 | nutrition | Dinh dưỡng | Nutrition | Chuyên ngành dinh dưỡng lâm sàng |
| 2 | sports-nutrition | Dinh dưỡng thể thao | Sports Nutrition | Dinh dưỡng cho vận động viên |

3.3. Ví dụ JSON fixture cho Django (`meal_types.json`)

```json
[
  {
    "model": "meal_plans.mealtypeconfig",
    "pk": 1,
    "fields": {"meal_type": "breakfast", "label": "Bữa sáng", "sort_order": 1}
  },
  {
    "model": "meal_plans.mealtypeconfig",
    "pk": 2,
    "fields": {"meal_type": "lunch", "label": "Bữa trưa", "sort_order": 2}
  }
]
```

## 4. Quy trình nạp dữ liệu (recommended pipeline)

1. Thực hiện ở môi trường dev/staging trước khi đưa vào production.
2. Chuẩn hóa và validate file nguồn (CSV/JSON) bằng script (kiểm tra required fields, unique constraints, giá trị hợp lệ).
3. Chạy import idempotent (management command hoặc fixtures).
4. Chạy sanity checks: đếm số bản ghi, kiểm tra ràng buộc khóa ngoại, chạy vài truy vấn sample.
5. Nếu OK, promote bản dữ liệu sang production; nếu lỗi, rollback theo bước 7.
6. Ghi log chi tiết (time, user, file, record counts, errors).
7. Rollback: script xóa batch bằng `source_version` tag hoặc restore từ backup nếu cần.

## 5. Cách implement trong Django

- Sử dụng Django fixtures (`manage.py loaddata`) cho dataset tĩnh nhỏ.
- Viết `management/commands/seed_<domain>.py` cho các dataset lớn hoặc cần logic (mapping, dedupe).
- Mỗi seed-command cần hỗ trợ flags:
  - `--dry-run`: kiểm tra nhưng không persist
  - `--force`: chấp nhận ghi đè
  - `--version`: tag version cho batch
  - `--backup`: tạo bảng tạm/backup trước khi ghi

Ví dụ skeleton command:

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--version')

    def handle(self, *args, **options):
        # load CSV
        # validate rows
        # create_or_update model instances (use get_or_create with unique fields)
        # print summary
```

## 6. Idempotency & deduplication

- Luôn dùng `unique`/`slug`/`code` fields để tránh tạo bản ghi trùng.
- Khi nạp, thực hiện `update_or_create()` hoặc `get()` + `update` để bảo đảm idempotency.
- Ghi `source` và `version` trên các bản ghi (nếu phù hợp) để dễ rollback.

## 7. Validation & kiểm tra sau nạp

Checklist sau import:

- Số bản ghi đúng theo manifest.
- Không có giá trị NULL trái phép trên các trường required.
- Không có duplicate keys.
- Kiểm tra các view/endpoint phụ thuộc (ví dụ: search API trả về kết quả cho category mới).
- Chạy unit/integration tests liên quan.

## 8. Rollback và backup

- Trước khi nạp, chụp snapshot DB (dump hoặc dump table) nếu dữ liệu production quan trọng.
- Sử dụng transaction nếu DB hỗ trợ: nhóm batch insert vào transaction để rollback tự động khi lỗi.
- Nếu dùng MySQL/Postgres: lưu sequence và trạng thái;
- Nếu rollback, dùng `source_version` để xoá các bản ghi cùng version, hoặc restore từ backup.

## 9. Ví dụ thực tế: nạp danh sách `provinces` và `meal_types`

1) Prepare `provinces.csv` với header: `code,name_vi,name_en`
2) Write `management/commands/seed_provinces.py`:
  - validate code unique
  - create_or_update Province model
3) Run:

```bash
python manage.py seed_provinces --version=2026-05-19
python manage.py seed_meal_types --version=2026-05-19
```

## 10. Kiểm thử & CI

- Thêm tests cho các management commands: test dry-run, test idempotency, test invalid rows.
- Trong CI, chạy seed dry-run với small sample files.

## 11. Giám sát & vận hành

- Ghi logs chi tiết cho mỗi job (stdout + file). Sử dụng monitoring để cảnh báo nếu counts khác thường.
- Lưu các file nguồn (CSV/JSON) kèm manifest trong repo hoặc lưu trữ phiên bản (S3/Git LFS) để audit.

## 12. Checklist triển khai nhanh (summary)

1. Chuẩn hóa file nguồn (CSV/JSON) và manifest.
2. Validate local/staging bằng `--dry-run`.
3. Backup production.
4. Chạy seed với `--version` và logs.
5. Chạy sanity checks và `manage.py check`.
6. Lưu artifacts (files, logs, sql-dump) cho audit.

---

Nếu bạn muốn, tôi sẽ:
- Sinh sẵn các file mẫu `provinces.csv`, `specializations.csv`, `meal_types.json` trong `tools/seeding/samples/`.
- Viết mẫu `management/commands/seed_provinces.py` để bạn chạy ngay.

# Khảo sát hệ thống: Quản lý dữ liệu thực phẩm & dinh dưỡng

## 1. Bối cảnh và bài toán
- Hệ thống phục vụ meal-planning, recipe và các module AI, dựa trên dữ liệu thực phẩm (foods, categories, nutrition).
- Vấn đề chính: dữ liệu nhập rời rạc, thiếu chuẩn hóa, nhiều thao tác thủ công trong quá trình ingest và chưa có quy trình phê duyệt/audit rõ ràng.

## 2. Đối tượng khảo sát và tác nhân
- Người dùng cuối: người lập kế hoạch bữa ăn, xem dinh dưỡng.
- Người quản trị / Data Steward: phê duyệt, merge, sửa lỗi dữ liệu.
- Tác nhân tự động: crawlers/ETL jobs, background workers, canonicalizer, validation services.
- Hệ thống tích hợp: database, external nutrition APIs, AI services, scheduler/queue.

## 3. Hiện trạng quy trình (As-Is)
- Luồng tổng quan: Crawl/thu thập → Lưu raw → Chuẩn hoá bằng script thủ công → Sửa/merge qua SQL/hand-edit → Publish.
- Vấn đề cụ thể:
  - Dữ liệu không nhất quán (tên, đơn vị, nhãn dinh dưỡng).
  - Trùng lặp, ID không nhất quán.
  - Quy trình không idempotent; re-run có thể tạo bản ghi đôi.
  - Thiếu observability: thiếu audit log, thiếu dashboard chất lượng import.
  - Migrations hoặc thay đổi model đôi khi gây lỗi vì thiếu compatibility wrapper.

## 4. Khó khăn chính
- Thiếu standardization và canonical categories.
- Quy trình nhập nhiều bước thủ công, dễ sai và khó lặp lại.
- Thiếu cơ chế phê duyệt có audit trước khi dữ liệu dùng cho sản phẩm.

## 5. Quy trình mục tiêu (To-Be)
- Mục tiêu: tự động hoá ingest, chuẩn hoá, mapping category có confidence, workflow phê duyệt, audit và publish an toàn.
- Luồng To-Be:
  1. Thu thập có kiểm soát (scheduler + retry/backoff + throttling).
 2. Lưu `raw` kèm metadata (nguồn, timestamp, checksum, pipeline version).
 3. Pipeline chuẩn hoá: normalize tên, chuẩn hoá đơn vị, parse dinh dưỡng.
 4. Canonical mapping với confidence score; nếu < threshold → đưa vào queue phê duyệt.
 5. Queue phê duyệt/merge bởi Data Steward (với audit log và ability to rollback).
 6. Publish sang bảng production và expose qua API versioned.

## 6. Luật nghiệp vụ cốt lõi (tóm tắt)
- R1 Traceability: mọi bản ghi phải lưu nguồn, timestamp, pipeline version; không ghi đè raw mà không ghi sửa đổi.
- R2 Dữ liệu tối thiểu: `name`, `serving_size` (kèm unit), và ít nhất một chỉ số dinh dưỡng (calories hoặc macronutrient).
- R3 Normalize tên: lưu `normalized_name`, giữ `display_name` và alias để tìm kiếm.
- R4 Canonical category: mỗi `food` phải map tới `canonical_category`. Nếu confidence < threshold → phê duyệt tay.
- R5 Trùng lặp & merge: key = (normalized_name + serving_size + brand); merge theo ưu tiên nguồn, tạo audit entry.
- R6 Idempotency: ingestion endpoints/queues phải idempotent.
- R7 Migration an toàn: chạy `manage.py check` trước apply migrations; không đổi FK quan trọng mà không có compatibility wrapper.
- R8 Phê duyệt & quyền: chỉ `Admin`/`Data Steward` có quyền merge/phê duyệt; mọi action được audit.
- R9 Validation & rejects: bản ghi fail validation → vào `rejected_items` với lý do, không publish.
- R10 API contract: dữ liệu xuất phải theo phiên bản contract; breaking change phải tăng version.

## 7. Kiểm tra & bàn giao
- Tạo tài liệu mô tả trên repository: file này `docs/system_survey.md`.
- Gợi ý bước tiếp theo: xuất ERD, sơ đồ To-Be (sequence/flow), và danh sách API/endpoint validation.

---
_Tạo bởi nội dung khảo sát tự động — cần review bởi Product Owner và Data Steward._

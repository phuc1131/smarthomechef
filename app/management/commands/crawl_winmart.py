import re
import time
import unicodedata
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection, transaction, IntegrityError

from services.external_apis import fetch_spoonacular_food, get_spoonacular_last_error
from apps.nutrition.models import Food, Ingredient, FoodCategory, IngredientPrice, IngredientNutrition
from app.services.nutrition_data_service import NutritionDataFiller
from app.config import WINMART_TIMEOUT, WINMART_RETRIES

try:
    import schedule
except ImportError:
    schedule = None


class Command(BaseCommand):
    help = 'Crawl WinMart products and categorize into foods or ingredients'

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    CRAWL_TARGETS = [
        # Rau, củ, trái cây (3 items)
        {'label': 'Rau củ trái cây - Rau lá', 'slug': 'rau-cu-trai-cay--c02', 'cate2': 'rau-la--c01167', 'is_food': False},
        {'label': 'Rau củ trái cây - Củ quả', 'slug': 'rau-cu-trai-cay--c02', 'cate2': 'cu-qua--c01168', 'is_food': False},
        {'label': 'Rau củ trái cây - Trái cây tươi', 'slug': 'rau-cu-trai-cay--c02', 'cate2': 'trai-cay-tuoi--c01173', 'is_food': False},

        # Sữa các loại (5 items)
        {'label': 'Sữa - Sữa tươi', 'slug': 'sua-cac-loai--c08', 'cate2': 'sua-tuoi--c0133', 'is_food': False},
        {'label': 'Sữa - Sữa hạt, sữa đậu', 'slug': 'sua-cac-loai--c08', 'cate2': 'sua-hat-sua-dau--c0134', 'is_food': False},
        {'label': 'Sữa - Bơ, sữa, phô mai', 'slug': 'sua-cac-loai--c08', 'cate2': 'bo-sua-pho-mai--c0138', 'is_food': False},
        {'label': 'Sữa - Sữa đặc', 'slug': 'sua-cac-loai--c08', 'cate2': 'sua-dac--c01161', 'is_food': False},
        {'label': 'Sữa - Sữa chua, váng sữa', 'slug': 'sua-cac-loai--c08', 'cate2': 'sua-chua-vang-sua--c01169', 'is_food': False},

        # Thịt, hải sản tươi (2 items)
        {'label': 'Thịt hải sản tươi - Thịt', 'slug': 'thit-hai-san-tuoi--c03', 'cate2': 'thit--c0111', 'is_food': False},
        {'label': 'Thịt hải sản tươi - Hải sản', 'slug': 'thit-hai-san-tuoi--c03', 'cate2': 'hai-san--c0113', 'is_food': False},

        # Bánh kẹo (4 items)
        {'label': 'Bánh kẹo - Bánh xốp, bánh quy', 'slug': 'banh-keo--c07', 'cate2': 'banh-xop-banh-quy--c0127', 'is_food': False},
        {'label': 'Bánh kẹo - Kẹo, chocolate', 'slug': 'banh-keo--c07', 'cate2': 'keo-chocolate--c0128', 'is_food': False},
        {'label': 'Bánh kẹo - Bánh snack', 'slug': 'banh-keo--c07', 'cate2': 'banh-snack--c0129', 'is_food': False},
        {'label': 'Bánh kẹo - Hạt, trái cây sấy khô', 'slug': 'banh-keo--c07', 'cate2': 'hat-trai-cay-say-kho--c0130', 'is_food': False},

        # Mì, thực phẩm ăn liền (4 items)
        {'label': 'Mì thực phẩm ăn liền - Mì', 'slug': 'mi-thuc-pham-an-lien--c34', 'cate2': 'mi--c01145', 'is_food': False},
        {'label': 'Mì thực phẩm ăn liền - Miến hủ, tiêu, bánh canh', 'slug': 'mi-thuc-pham-an-lien--c34', 'cate2': 'mien-hu-tiu-banh-canh--c01148', 'is_food': False},
        {'label': 'Mì thực phẩm ăn liền - Cháo', 'slug': 'mi-thuc-pham-an-lien--c34', 'cate2': 'chao--c01146', 'is_food': False},
        {'label': 'Mì thực phẩm ăn liền - Phở, bún', 'slug': 'mi-thuc-pham-an-lien--c34', 'cate2': 'pho-bun--c01147', 'is_food': False},
        # Thực phẩm khô (6 items)
        {'label': 'Thực phẩm khô - Gạo, nông sản khô', 'slug': 'thuc-pham-kho--c06', 'cate2': 'gao-nong-san-kho--c0120', 'is_food': False},
        {'label': 'Thực phẩm khô - Ngũ cốc, yến mạch', 'slug': 'thuc-pham-kho--c06', 'cate2': 'ngu-coc-yen-mach--c0122', 'is_food': False},
        {'label': 'Thực phẩm khô - Thực phẩm đông hộp', 'slug': 'thuc-pham-kho--c06', 'cate2': 'thuc-pham-dong-hop--c0123', 'is_food': False},
        # URL duplicated by source input, kept intentionally; runtime dedupe will skip this duplicate key.
        {'label': 'Thực phẩm khô - Thực phẩm đông hộp (duplicate input)', 'slug': 'thuc-pham-kho--c06', 'cate2': 'thuc-pham-dong-hop--c0123', 'is_food': False},
        {'label': 'Thực phẩm khô - Rong biển, tảo biển', 'slug': 'thuc-pham-kho--c06', 'cate2': 'rong-bien-tao-bien--c0124', 'is_food': False},
        {'label': 'Thực phẩm khô - Bột các loại', 'slug': 'thuc-pham-kho--c06', 'cate2': 'bot-cac-loai--c0125', 'is_food': False},
        {'label': 'Thực phẩm khô - Thực phẩm chay', 'slug': 'thuc-pham-kho--c06', 'cate2': 'thuc-pham-chay--c01166', 'is_food': False},
        # Thực phẩm chế biến (5 items)
        {'label': 'Thực phẩm chế biến - Bánh mì', 'slug': 'thuc-pham-che-bien--c04', 'cate2': 'banh-mi--c0115', 'is_food': False},
        {'label': 'Thực phẩm chế biến - Xúc xích, thịt ngưòi', 'slug': 'thuc-pham-che-bien--c04', 'cate2': 'xuc-xich-thit-nguoi--c0156', 'is_food': False},
        {'label': 'Thực phẩm chế biến - Bánh bao', 'slug': 'thuc-pham-che-bien--c04', 'cate2': 'banh-bao--c01156', 'is_food': False},
        {'label': 'Thực phẩm chế biến - Kim chi', 'slug': 'thuc-pham-che-bien--c04', 'cate2': 'kim-chi--c01157', 'is_food': False},
        {'label': 'Thực phẩm chế biến - Thực phẩm chế biến khác', 'slug': 'thuc-pham-che-bien--c04', 'cate2': 'thuc-pham-che-bien-khac--c0114', 'is_food': False},
        # Gia vị (7 items)
        {'label': 'Gia vị - Dầu ăn', 'slug': 'gia-vi--c35', 'cate2': 'dau-an--c01149', 'is_food': False},
        {'label': 'Gia vị - Nước mắm, nước chấm', 'slug': 'gia-vi--c35', 'cate2': 'nuoc-mam-nuoc-cham--c01150', 'is_food': False},
        {'label': 'Gia vị - Đường', 'slug': 'gia-vi--c35', 'cate2': 'duong--c01151', 'is_food': False},
        {'label': 'Gia vị - Nước tương', 'slug': 'gia-vi--c35', 'cate2': 'nuoc-tuong--c01152', 'is_food': False},
        {'label': 'Gia vị - Hạt nêm', 'slug': 'gia-vi--c35', 'cate2': 'hat-nem--c01153', 'is_food': False},
        {'label': 'Gia vị - Tương các loại', 'slug': 'gia-vi--c35', 'cate2': 'tuong-cac-loai--c01154', 'is_food': False},
        {'label': 'Gia vị - Gia vị khác', 'slug': 'gia-vi--c35', 'cate2': 'gia-vi-khac--c01155', 'is_food': False},
        # Thực phẩm đông lạnh (5 items)
        {'label': 'Thực phẩm đông lạnh - Hải sản đông lạnh', 'slug': 'thuc-pham-dong-lanh--c05', 'cate2': 'hai-san-dong-lanh--c0157', 'is_food': False},
        {'label': 'Thực phẩm đông lạnh - Thịt đông lạnh', 'slug': 'thuc-pham-dong-lanh--c05', 'cate2': 'thit-dong-lanh--c01158', 'is_food': False},
        {'label': 'Thực phẩm đông lạnh - Chả giò', 'slug': 'thuc-pham-dong-lanh--c05', 'cate2': 'cha-gio--c01159', 'is_food': False},
        {'label': 'Thực phẩm đông lạnh - Cá, bò viên', 'slug': 'thuc-pham-dong-lanh--c05', 'cate2': 'ca-bo-vien--c01160', 'is_food': False},
        {'label': 'Thực phẩm đông lạnh - Thực phẩm đông lạnh khác', 'slug': 'thuc-pham-dong-lanh--c05', 'cate2': 'thuc-pham-dong-lanh-khac--c0158', 'is_food': False},
        # Trứng, đậu hũ (2 items)
        {'label': 'Trứng, đậu hũ - Trứng', 'slug': 'trung-dau-hu--c33', 'cate2': 'trung--c01165', 'is_food': False},
        {'label': 'Trứng, đậu hũ - Đậu hũ', 'slug': 'trung-dau-hu--c33', 'cate2': 'dau-hu--c01138', 'is_food': False},
    ]

    API_TEMPLATE = (
        'https://api-crownx.winmart.vn/it/api/web/v3/item/category'
        '?orderByDesc=true&pageNumber={page}&pageSize=1000&slug={slug}&storeCode=1535&storeGroupCode=1998&cate2={cate2}'
    )

    WEB_URL_TEMPLATE = 'https://winmart.vn/{slug}?cate2={cate2}'

    def add_arguments(self, parser):
        parser.add_argument('--limit-categories', type=int, default=None,
                            help='Limit number of categories to crawl')
        parser.add_argument('--limit-items', type=int, default=None,
                            help='Limit number of items per category')
        parser.add_argument('--reset-ingredients-before-crawl', action='store_true',
                            help='Reset ingredient tables before crawl (optional, not default)')
        parser.add_argument('--compact-category-ids', action='store_true',
                    help='Compact FoodCategory IDs to match configured target order')
        parser.add_argument('--prepare-categories-only', action='store_true',
                            help='Only create target food categories, do not crawl items')
        parser.add_argument('--schedule', action='store_true',
                            help='Run crawl automatically at 00:00 and 12:00 each day')

    def _select_targets(self, limit_categories=None):
        raw_targets = self.CRAWL_TARGETS[:limit_categories] if limit_categories else self.CRAWL_TARGETS
        selected = []
        seen = set()
        duplicate_count = 0

        for target in raw_targets:
            key = (target.get('slug'), target.get('cate2'))
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)
            selected.append(target)

        if duplicate_count:
            self.stdout.write(self.style.WARNING(
                f'Skipped {duplicate_count} duplicate crawl targets from configured URL list.'
            ))

        return selected

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        return re.sub(r'_+', '_', text).strip('_')

    @staticmethod
    def parse_price(item: dict) -> Tuple[Optional[float], str]:
        """
        Lấy giá thực tế hiển thị trên web theo thứ tự ưu tiên:
          1. salePrice   - giá khuyến mãi / giá hội viên (màu đỏ trên web)
          2. price       - giá bán thông thường
          3. retailPrice - giá bán lẻ gốc (fallback cuối)

        WinMart hiển thị salePrice khi có khuyến mãi, ngược lại dùng price/retailPrice.
        Lấy giá nhỏ hơn giữa salePrice và price để đảm bảo đúng giá hiển thị.
        """
        unit = item.get('uom') or item.get('unit') or ''

        def to_float(raw) -> Optional[float]:
            if raw in (None, '', 0, '0'):
                return None
            s = str(raw)
            s = s.replace('₫', '').replace('đ', '').replace('VND', '').strip()
            digits = re.sub(r'[^0-9]', '', s)
            if not digits:
                return None
            try:
                return float(digits)
            except Exception:
                return None

        sale_price = to_float(item.get('salePrice'))
        normal_price = to_float(item.get('price'))
        retail_price = to_float(
            item.get('retailPrice') or item.get('retail_price') or item.get('retail')
        )

        # Giá hiển thị trên web = giá nhỏ nhất trong các giá hợp lệ
        # (WinMart luôn hiện giá thấp nhất cho người dùng)
        candidates = [p for p in [sale_price, normal_price, retail_price] if p and p > 0]
        final_price = min(candidates) if candidates else None

        return final_price, unit.upper() if unit else ''

    @staticmethod
    def extract_nutrition(html: str) -> str:
        text = BeautifulSoup(html or '', 'html.parser').get_text(" ", strip=True)
        match = re.search(r'Dinh duong\s*[:：]\s*(.*)', text, re.IGNORECASE)
        return match.group(1) if match else ''

    @staticmethod
    def parse_nutrition(text: str) -> Dict[str, float]:
        def find(pattern):
            if not text:
                return 0.0
            m = re.search(pattern, text.lower())
            if not m:
                return 0.0
            raw = (m.group(1) or '').strip().replace(',', '.')
            try:
                return float(raw)
            except Exception:
                return 0.0

        return {
            'calories': find(r'(?:calories?|calor|kcal)[^\d]*(\d+(?:[.,]\d+)?)'),
            'protein':  find(r'(?:protein|dam|chat dam)[^\d]*(\d+(?:[.,]\d+)?)'),
            'carbs':    find(r'(?:carb|carbon|tinh bot|glucose)[^\d]*(\d+(?:[.,]\d+)?)'),
            'fat':      find(r'(?:fat|beo|chat beo)[^\d]*(\d+(?:[.,]\d+)?)'),
            'fiber':    find(r'(?:fiber|xo|chat xo)[^\d]*(\d+(?:[.,]\d+)?)')
        }

    @staticmethod
    def _needs_nutrition_completion(nutrition: Dict[str, float]) -> bool:
        if not nutrition:
            return True
        required_fields = ('calories', 'protein', 'carbs', 'fat', 'fiber')
        return any((nutrition.get(field) or 0.0) <= 0.0 for field in required_fields)

    def enrich_missing_nutrition_with_spoonacular(self, item: dict) -> dict:
        current = dict(item.get('nutrition') or {})
        if not self._needs_nutrition_completion(current):
            return item

        payload = fetch_spoonacular_food(item.get('name') or '')
        if not isinstance(payload, dict):
            return item

        incoming = payload.get('nutrition') or {}
        if not isinstance(incoming, dict):
            return item

        mapped = {
            'calories': incoming.get('calories'),
            'protein':  incoming.get('protein'),
            'carbs':    incoming.get('carbs', incoming.get('carbohydrates')),
            'fat':      incoming.get('fat'),
            'fiber':    incoming.get('fiber'),
        }

        updated = False
        for key, value in mapped.items():
            if (current.get(key) or 0.0) > 0.0:
                continue
            try:
                number = float(str(value)) if value is not None else 0.0
            except Exception:
                number = 0.0
            if number > 0.0:
                current[key] = number
                updated = True

        item['nutrition'] = current
        item['spoonacular_enriched'] = updated
        return item

    # -------------------------------------------------------------------------
    # Category helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def category_name_from_cate2(cate2: str) -> str:
        raw = (cate2 or '').strip().lower()
        if not raw:
            return 'Unknown'
        slug_part = raw.split('--', 1)[0]
        words = [p for p in slug_part.split('-') if p]
        return ' '.join(w.capitalize() for w in words) if words else 'Unknown'

    def get_or_create_category(self, category_name: str):
        """Return (or create) the canonical FoodCategory row for *category_name*."""
        normalized = (category_name or '').strip() or 'Unknown'

        # Prefer an exact-case match first, then case-insensitive.
        obj = (
            FoodCategory.objects.filter(name=normalized).order_by('id').first()
            or FoodCategory.objects.filter(name__iexact=normalized).order_by('id').first()
        )
        if obj:
            return obj

        # Try to create; guard against race/unique violations by catching IntegrityError
        try:
            return FoodCategory.objects.create(name=normalized)
        except IntegrityError:
            # Another process may have created it with different casing; fetch canonical row
            existing = FoodCategory.objects.filter(name__iexact=normalized).order_by('id').first()
            if existing:
                return existing
            # As a last resort, re-raise
            raise

    def ensure_target_categories(self, limit_categories=None):
        targets = self._select_targets(limit_categories=limit_categories)
        created = existing = 0
        self.stdout.write(self.style.SUCCESS('\nPreparing categories before crawl...'))
        for t in targets:
            name = self.category_name_from_cate2(t['cate2'])
            before = FoodCategory.objects.filter(name__iexact=name).exists()
            self.get_or_create_category(name)
            existing += before
            created += not before
        self.stdout.write(self.style.SUCCESS(
            f'Prepared categories: total={len(targets)} created={created} existing={existing}'
        ))

    def deduplicate_target_categories(self, limit_categories=None):
        """Merge case-variant duplicates into one canonical row."""
        targets = self._select_targets(limit_categories=limit_categories)
        merged_pairs = 0
        for t in targets:
            canonical = self.category_name_from_cate2(t['cate2'])
            candidates = list(FoodCategory.objects.filter(name__iexact=canonical).order_by('id'))
            if len(candidates) < 2:
                continue
            keeper = next((c for c in candidates if c.name == canonical), candidates[0])
            for dup in candidates:
                if dup.id == keeper.id:
                    continue
                Food.objects.filter(category_id=dup.id).update(category_id=keeper.id)
                dup.delete()
                merged_pairs += 1
        msg = f'Deduplicated category rows: merged={merged_pairs}'
        self.stdout.write(self.style.WARNING(msg) if merged_pairs else self.style.SUCCESS(msg))

    @transaction.atomic
    def compact_category_ids(self, limit_categories=None):
        """Re-number FoodCategory PKs to be contiguous (1, 2, 3 …)."""
        targets = self._select_targets(limit_categories=limit_categories)
        target_names = [self.category_name_from_cate2(t['cate2']) for t in targets]

        existing_rows = list(FoodCategory.objects.order_by('id').values('id', 'name'))
        if not existing_rows:
            return

        db_names = [r['name'] for r in existing_rows]
        ordered = []
        for name in target_names:
            if name in db_names and name not in ordered:
                ordered.append(name)
        for name in db_names:
            if name not in ordered:
                ordered.append(name)

        old_by_name = {r['name']: r['id'] for r in existing_rows}
        mapping = [(old_by_name[n], new_id, n) for new_id, n in enumerate(ordered, start=1)]

        if all(old == new for old, new, _ in mapping):
            self.stdout.write(self.style.SUCCESS('Category ID compaction: no gaps detected'))
            return

        shadow_base = max(r['id'] for r in existing_rows) + 1000
        shadow_mapping = [(old, shadow_base + i, new, n) for i, (old, new, n) in enumerate(mapping, 1)]

        # Phase 1 → shadow IDs
        for old, shadow, _, _ in shadow_mapping:
            FoodCategory.objects.filter(id=old).update(name=f'__old__{old}')
        for _, shadow, _, name in shadow_mapping:
            FoodCategory.objects.create(id=shadow, name=name)
        for old, shadow, _, _ in shadow_mapping:
            Food.objects.filter(category_id=old).update(category_id=shadow)
        for old, _, _, _ in shadow_mapping:
            FoodCategory.objects.filter(id=old).delete()

        # Phase 2 → final contiguous IDs
        for _, shadow, _, _ in shadow_mapping:
            FoodCategory.objects.filter(id=shadow).update(name=f'__shadow__{shadow}')
        for _, _, new, name in shadow_mapping:
            FoodCategory.objects.create(id=new, name=name)
        for _, shadow, new, _ in shadow_mapping:
            Food.objects.filter(category_id=shadow).update(category_id=new)
        for _, shadow, _, _ in shadow_mapping:
            FoodCategory.objects.filter(id=shadow).delete()

        max_id = FoodCategory.objects.order_by('-id').values_list('id', flat=True).first() or 1
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('food_categories','id'), %s, true)",
                [max_id],
            )
        self.stdout.write(self.style.SUCCESS('Category ID compaction: completed'))

    # -------------------------------------------------------------------------
    # Food upsert helpers (KEY SECTION – rewritten)
    # -------------------------------------------------------------------------

    def _upsert_food(self, name: str, category_id: int, fields: dict) -> tuple:
        """
        Insert-or-update a Food row identified by its *name* (case-insensitive).

        Rules
        -----
        • If a row with the same name already exists → update ALL fields with the
          newest crawled values (overwrite), keep the existing PK.
        • If no row exists → insert a brand-new row; Django assigns the next
          sequential PK automatically via the DB sequence.
        • Only one row per name is ever kept.  Duplicate rows created by previous
          runs are removed before the upsert (keeping the lowest PK as canonical).

        Returns (food_instance, created: bool).
        """
        base_name = (name or '').strip()
        if not base_name:
            return None, False

        # --- resolve duplicates first (safety net) ---
        duplicates = list(
            Food.objects.filter(name__iexact=base_name).order_by('id')
        )
        if len(duplicates) > 1:
            canonical = duplicates[0]
            for dup in duplicates[1:]:
                dup.delete()
        elif len(duplicates) == 1:
            canonical = duplicates[0]
        else:
            canonical = None

        if canonical:
            # UPDATE: overwrite every field with the freshest data
            canonical.name        = base_name          # keep casing from latest crawl
            canonical.category_id = category_id
            for field_name, field_value in fields.items():
                setattr(canonical, field_name, field_value)
            canonical.save()
            return canonical, False

        # INSERT: let the DB assign the next sequential ID
        new_food = Food.objects.create(name=base_name, category_id=category_id, **fields)
        return new_food, True

    def resequence_food_ids(self):
        """
        Compact the Food table so every PK equals its row's ordinal position
        (1, 2, 3 …).  Call once after all targets have been saved.

        The two-phase shadow approach avoids PK conflicts:
          Phase 1: move every row to a temporary high shadow ID.
          Phase 2: move every row from its shadow ID to its final sequential ID.
        """
        rows = list(Food.objects.order_by('id').values_list('id', flat=True))
        if not rows:
            return

        if rows == list(range(1, len(rows) + 1)):
            self.stdout.write(self.style.SUCCESS('Food ID resequence: already contiguous'))
            return

        shadow_base = rows[-1] + 10_000

        # Phase 1 – move to shadow IDs to free up the target IDs
        with connection.cursor() as cur:
            for seq, old_id in enumerate(rows, start=1):
                shadow_id = shadow_base + seq
                cur.execute(
                    "UPDATE foods SET id = %s WHERE id = %s",
                    [shadow_id, old_id],
                )

        # Phase 2 – move from shadow IDs to final sequential IDs
        with connection.cursor() as cur:
            for seq in range(1, len(rows) + 1):
                shadow_id = shadow_base + seq
                cur.execute(
                    "UPDATE foods SET id = %s WHERE id = %s",
                    [seq, shadow_id],
                )

        # Reset the sequence so future inserts continue after the last row
        with connection.cursor() as cur:
            cur.execute(
                "SELECT setval(pg_get_serial_sequence('foods','id'), %s, true)",
                [len(rows)],
            )

        self.stdout.write(self.style.SUCCESS(
            f'Food ID resequence: compacted {len(rows)} rows to IDs 1–{len(rows)}'
        ))

    # -------------------------------------------------------------------------
    # Pre-crawl cleanup
    # -------------------------------------------------------------------------

    def clear_ingredients_before_crawl(self):
        """Remove all ingredient data + orphan prices/nutrition to ensure fresh crawl without duplicates."""
        with connection.cursor() as cursor:
            # Bước 1: Kiểm tra và xóa orphan records (ingredient_prices/nutrition không có ingredient)
            cursor.execute("""
                SELECT COUNT(*) FROM ingredient_prices ip
                WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ip.ingredient_id)
            """)
            orphan_prices = cursor.fetchone()[0]
            
            if orphan_prices > 0:
                cursor.execute("""
                    DELETE FROM ingredient_prices
                    WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ingredient_id)
                """)
                self.stdout.write(self.style.WARNING(f'  Removed {orphan_prices} orphan ingredient_prices'))
            
            cursor.execute("""
                SELECT COUNT(*) FROM ingredient_nutrition in_nut
                WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = in_nut.ingredient_id)
            """)
            orphan_nutrition = cursor.fetchone()[0]
            
            if orphan_nutrition > 0:
                cursor.execute("""
                    DELETE FROM ingredient_nutrition
                    WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ingredient_id)
                """)
                self.stdout.write(self.style.WARNING(f'  Removed {orphan_nutrition} orphan ingredient_nutrition'))
            
            # Bước 2: Xóa toàn bộ dữ liệu ingredients và related tables
            cursor.execute("SELECT COUNT(*) FROM ingredients")
            old_count = cursor.fetchone()[0]
            
            if old_count > 0:
                # Delete related records trước (orders matter for FK constraints)
                cursor.execute("DELETE FROM ingredient_prices WHERE ingredient_id IS NOT NULL")
                cursor.execute("DELETE FROM ingredient_nutrition WHERE ingredient_id IS NOT NULL")
                cursor.execute("DELETE FROM ingredients")
                self.stdout.write(self.style.WARNING(f'  Cleared {old_count} old ingredients'))
            
            # Bước 3: Reset tất cả sequences để ID bắt đầu từ 1
            cursor.execute("SELECT setval(pg_get_serial_sequence('ingredients','id'), 1, false)")
            cursor.execute("SELECT setval(pg_get_serial_sequence('ingredient_prices','id'), 1, false)")
            cursor.execute("SELECT setval(pg_get_serial_sequence('ingredient_nutrition','id'), 1, false)")
            
            connection.commit()
            self.stdout.write(self.style.SUCCESS('  All ingredient sequences reset to 1'))

    # -------------------------------------------------------------------------
    # Ingredient upsert helpers (mirrors Food logic)
    # -------------------------------------------------------------------------

    def _upsert_ingredient(self, name: str, fields: dict, nutrition: dict, price: Optional[float], unit: str) -> tuple:
        """
        Insert-or-update an Ingredient row identified by its *name* (case-insensitive).

        Rules
        -----
        • If a row with the same name already exists → update ALL fields with the
          newest crawled values (overwrite), keep the existing PK.
        • If no row exists → insert a brand-new row; DB assigns next sequential PK.
        • Only one row per name is ever kept — duplicates (lowest PK kept) are removed.
        • Related IngredientNutrition and IngredientPrice are always overwritten too.

        Returns (ingredient_instance, created: bool).
        """
        base_name = (name or '').strip()
        if not base_name:
            return None, False

        # --- resolve duplicates first (safety net) ---
        duplicates = list(
            Ingredient.objects.filter(name__iexact=base_name).order_by('id')
        )
        if len(duplicates) > 1:
            canonical = duplicates[0]
            # Re-point any related rows to the keeper before deleting duplicates
            for dup in duplicates[1:]:
                IngredientNutrition.objects.filter(ingredient_id=dup.id).delete()
                IngredientPrice.objects.filter(ingredient_id=dup.id).delete()
                dup.delete()
        elif len(duplicates) == 1:
            canonical = duplicates[0]
        else:
            canonical = None

        if canonical:
            # UPDATE: overwrite base fields with latest crawled values
            canonical.name            = base_name
            canonical.normalized_name = fields.get('normalized_name', canonical.normalized_name)
            canonical.save()
            created = False
        else:
            # INSERT: DB assigns next sequential ID
            canonical = Ingredient.objects.create(
                name=base_name,
                normalized_name=fields.get('normalized_name', ''),
            )
            created = True

        # Always overwrite nutrition (update_or_create → full overwrite via defaults)
        IngredientNutrition.objects.update_or_create(
            ingredient_id=canonical.id,
            defaults={
                'calories': Decimal(str(nutrition.get('calories', 0))),
                'protein':  Decimal(str(nutrition.get('protein',  0))),
                'carbs':    Decimal(str(nutrition.get('carbs',    0))),
                'fat':      Decimal(str(nutrition.get('fat',      0))),
                'fiber':    Decimal(str(nutrition.get('fiber',    0))),
            }
        )

        # Always overwrite price for the same unit_type
        if price:
            unit_key = unit or 'UNIT'
            IngredientPrice.objects.update_or_create(
                ingredient_id=canonical.id,
                unit_type=unit_key,
                defaults={'price_per_unit': Decimal(str(price))}
            )

        return canonical, created

    def resequence_ingredient_ids(self):
        """
        Compact the Ingredient table so every PK equals its row's ordinal position
        (1, 2, 3 …).  Uses the same two-phase shadow approach as resequence_food_ids.

        Note: IngredientNutrition and IngredientPrice reference ingredient_id via FK,
        so we must update those in tandem.
        """
        rows = list(Ingredient.objects.order_by('id').values_list('id', flat=True))
        if not rows:
            return

        if rows == list(range(1, len(rows) + 1)):
            self.stdout.write(self.style.SUCCESS('Ingredient ID resequence: already contiguous'))
            return

        shadow_base = rows[-1] + 10_000

        # Phase 1 – move to shadow IDs
        with connection.cursor() as cur:
            for seq, old_id in enumerate(rows, start=1):
                shadow_id = shadow_base + seq
                cur.execute("UPDATE ingredients            SET id             = %s WHERE id             = %s", [shadow_id, old_id])
                cur.execute("UPDATE ingredient_nutritions  SET ingredient_id  = %s WHERE ingredient_id  = %s", [shadow_id, old_id])
                cur.execute("UPDATE ingredient_prices      SET ingredient_id  = %s WHERE ingredient_id  = %s", [shadow_id, old_id])

        # Phase 2 – move to final sequential IDs
        with connection.cursor() as cur:
            for seq in range(1, len(rows) + 1):
                shadow_id = shadow_base + seq
                cur.execute("UPDATE ingredients            SET id             = %s WHERE id             = %s", [seq, shadow_id])
                cur.execute("UPDATE ingredient_nutritions  SET ingredient_id  = %s WHERE ingredient_id  = %s", [seq, shadow_id])
                cur.execute("UPDATE ingredient_prices      SET ingredient_id  = %s WHERE ingredient_id  = %s", [seq, shadow_id])

        # Reset the sequence so future inserts continue correctly
        with connection.cursor() as cur:
            cur.execute(
                "SELECT setval(pg_get_serial_sequence('ingredients','id'), %s, true)",
                [len(rows)],
            )

        self.stdout.write(self.style.SUCCESS(
            f'Ingredient ID resequence: compacted {len(rows)} rows to IDs 1–{len(rows)}'
        ))

    def verify_ingredient_data_integrity(self):
        """
        Verify that ingredient_prices & ingredient_nutrition data matches ingredients.
        - Remove orphan records (no matching ingredient)
        - Check for duplicate unit_types
        - Validate FK references
        """
        with connection.cursor() as cur:
            # Check orphan ingredient_prices
            cur.execute("""
                SELECT COUNT(*) FROM ingredient_prices ip
                WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ip.ingredient_id)
            """)
            orphan_prices = cur.fetchone()[0]
            if orphan_prices > 0:
                cur.execute("""
                    DELETE FROM ingredient_prices
                    WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ingredient_id)
                """)
                self.stdout.write(self.style.WARNING(f'  Removed {orphan_prices} orphan ingredient_prices'))
            
            # Check orphan ingredient_nutrition
            cur.execute("""
                SELECT COUNT(*) FROM ingredient_nutrition in_nut
                WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = in_nut.ingredient_id)
            """)
            orphan_nutrition = cur.fetchone()[0]
            if orphan_nutrition > 0:
                cur.execute("""
                    DELETE FROM ingredient_nutrition
                    WHERE NOT EXISTS (SELECT 1 FROM ingredients i WHERE i.id = ingredient_id)
                """)
                self.stdout.write(self.style.WARNING(f'  Removed {orphan_nutrition} orphan ingredient_nutrition'))
            
            # Check for duplicate prices for same ingredient
            cur.execute("""
                SELECT ingredient_id, unit_type, COUNT(*) as cnt
                FROM ingredient_prices
                GROUP BY ingredient_id, unit_type
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            if duplicates:
                self.stdout.write(self.style.WARNING(f'  Found {len(duplicates)} duplicate price entries:'))
                for ing_id, unit_type, cnt in duplicates:
                    # Keep oldest, delete newer
                    cur.execute("""
                        DELETE FROM ingredient_prices
                        WHERE ingredient_id = %s AND unit_type = %s AND id NOT IN (
                            SELECT id FROM ingredient_prices
                            WHERE ingredient_id = %s AND unit_type = %s
                            ORDER BY updated_at ASC LIMIT 1
                        )
                    """, [ing_id, unit_type, ing_id, unit_type])
                    self.stdout.write(f'    - Ingredient {ing_id} ({unit_type}): kept oldest, removed {cnt-1}')
            
            # Verify all ingredients have at least price OR nutrition
            cur.execute("""
                SELECT COUNT(*) FROM ingredients i
                WHERE NOT EXISTS (SELECT 1 FROM ingredient_prices ip WHERE ip.ingredient_id = i.id)
                  AND NOT EXISTS (SELECT 1 FROM ingredient_nutrition in_n WHERE in_n.ingredient_id = i.id)
            """)
            missing_data = cur.fetchone()[0]
            if missing_data > 0:
                self.stdout.write(self.style.WARNING(f'  {missing_data} ingredients missing both price & nutrition data'))
            
            connection.commit()
            self.stdout.write(self.style.SUCCESS('  Ingredient data integrity verified'))

    # -------------------------------------------------------------------------
    # Crawl
    # -------------------------------------------------------------------------

    def crawl(self, limit_categories=None, limit_items=None):
        self.stdout.write(self.style.SUCCESS('CRAWLING DATA FROM WINMART...'))
        self.stdout.write('=' * 80)

        targets = self._select_targets(limit_categories=limit_categories)
        failures = []

        for target in targets:
            slug   = target['slug']
            cate2  = target['cate2']
            label  = target['label']
            category_name = self.category_name_from_cate2(cate2)
            self.get_or_create_category(category_name)

            self.stdout.write(f'\n[{label}]')
            self.stdout.write(f"  URL: {self.WEB_URL_TEMPLATE.format(slug=slug, cate2=cate2)}")

            target_items = []
            page = 1
            total_items = 0

            while True:
                url = self.API_TEMPLATE.format(page=page, slug=slug, cate2=cate2)
                try:
                    # Retry loop with exponential/backoff-like delay
                    last_exc = None
                    items = []
                    for attempt in range(1, max(1, WINMART_RETRIES) + 1):
                        try:
                            res = requests.get(url, headers=self.HEADERS, timeout=WINMART_TIMEOUT)
                            data = res.json().get('data', {})
                            items = data.get('items', [])
                            last_exc = None
                            break
                        except Exception as exc:
                            last_exc = exc
                            self.stdout.write(self.style.WARNING(f'  Error on page {page} (attempt {attempt}/{WINMART_RETRIES}): {exc}'))
                            if attempt < WINMART_RETRIES:
                                # simple backoff: sleep a few seconds proportional to attempt
                                time.sleep(attempt * 2)

                    if last_exc and not items:
                        # All retries failed for this page
                        self.stdout.write(self.style.WARNING(f'  Giving up on page {page} after {WINMART_RETRIES} attempts'))
                        failures.append({'label': label, 'slug': slug, 'cate2': cate2, 'page': page, 'error': str(last_exc)})
                        break

                    if not items:
                        self.stdout.write(f'  OK Total: {total_items} items')
                        break

                    for item in items:
                        name = item.get('name', '')
                        if not name:
                            continue

                        norm   = self.normalize_text(name)
                        price, unit = self.parse_price(item)

                        long_desc      = item.get('longDescription', '')
                        nutrition_text = self.extract_nutrition(long_desc)
                        nutrition      = self.parse_nutrition(nutrition_text)

                        image_url = item.get('imageString', '') or item.get('image', '')
                        if image_url and not image_url.startswith('http'):
                            image_url = 'https://cdn.winmart.vn' + image_url

                        description = item.get('description', '') or item.get('shortDescription', '')

                        target_items.append({
                            'name':             name,
                            'normalized_name':  norm,
                            'category_display': label,
                            'category_name':    category_name,
                            'category_slug':    slug,
                            'cate2':            cate2,
                            'price':            price,
                            'unit':             unit,
                            'nutrition':        nutrition,
                            'is_food':          bool(target.get('is_food', False)),
                            'image_url':        image_url,
                            'description':      description,
                            'source_url':       self.WEB_URL_TEMPLATE.format(slug=slug, cate2=cate2),
                        })

                    self.stdout.write(f'  Page {page}: {len(items)} items (Total: {total_items + len(items)})')
                    total_items += len(items)
                    page += 1

                    if limit_items and total_items >= limit_items:
                        break

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error on page {page}: {e}'))
                    break

            self.save_target_to_database(target, target_items)

        self.stdout.write('\n' + '=' * 80)
        if failures:
            self.stdout.write(self.style.WARNING('\nSome targets failed during crawl:'))
            for f in failures:
                self.stdout.write(self.style.WARNING(f" - {f['label']} ({f['slug']}?cate2={f['cate2']}) failed on page {f['page']}: {f['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll targets processed or gracefully skipped.'))

    # -------------------------------------------------------------------------
    # Save to DB
    # -------------------------------------------------------------------------

    @transaction.atomic
    def save_target_to_database(self, target, data):
        """
        Persist one crawl target's items.

        Food rows
        ---------
        • Identified by name (case-insensitive).
        • Duplicate names → keep lowest PK, overwrite with latest data.
        • New names        → insert; DB assigns the next sequential PK.
        • category_id      → always taken from the canonical FoodCategory row.

        Ingredient rows follow the original logic (unchanged).
        """
        foods_created        = 0
        foods_updated        = 0
        ingredients_created  = 0
        ingredients_updated  = 0
        spoonacular_enabled       = True
        spoonacular_disabled_reason = None

        self.stdout.write(self.style.SUCCESS(
            f'\nProcessing and saving {len(data)} items for {target["label"]}...'
        ))

        category_id_cache: dict[str, int] = {}

        for i, item in enumerate(data, 1):

            # ---- FOOD --------------------------------------------------------
            if item['is_food']:
                # Optional Spoonacular enrichment
                if spoonacular_enabled:
                    item = self.enrich_missing_nutrition_with_spoonacular(item)
                    last_error = (get_spoonacular_last_error() or '').lower()
                    if 'quota' in last_error or 'han muc' in last_error:
                        spoonacular_enabled = False
                        spoonacular_disabled_reason = get_spoonacular_last_error()
                        self.stdout.write(self.style.WARNING(
                            f'Spoonacular enrichment disabled: {spoonacular_disabled_reason}'
                        ))

                # Resolve category_id (cached per name)
                cat_name = item['category_name']
                if cat_name not in category_id_cache:
                    category_id_cache[cat_name] = self.get_or_create_category(cat_name).id
                category_id = category_id_cache[cat_name]

                food_fields = {
                    'calories':        Decimal(str(item['nutrition'].get('calories', 0))),
                    'protein':         Decimal(str(item['nutrition'].get('protein',  0))),
                    'carbs':           Decimal(str(item['nutrition'].get('carbs',    0))),
                    'fat':             Decimal(str(item['nutrition'].get('fat',      0))),
                    'fiber':           Decimal(str(item['nutrition'].get('fiber',    0))),
                    'normalized_name': item['normalized_name'],
                    'image_url':       item.get('image_url', ''),
                    'description':     item.get('description', ''),
                }

                food_obj, created = self._upsert_food(
                    name=item['name'],
                    category_id=category_id,
                    fields=food_fields,
                )

                if food_obj and self._needs_nutrition_completion(item.get('nutrition') or {}):
                    NutritionDataFiller.fill_missing_nutrition(food_obj, use_spoonacular=True, use_gemini=True)

                if created:
                    foods_created += 1
                else:
                    foods_updated += 1

                if item.get('spoonacular_enriched'):
                    self.stdout.write(f"  [Spoonacular] Enriched: {item['name']}")

            # ---- INGREDIENT --------------------------------------------------
            else:
                ingredient_obj, created = self._upsert_ingredient(
                    name=item['name'],
                    fields={'normalized_name': item['normalized_name']},
                    nutrition=item['nutrition'],
                    price=item['price'],
                    unit=item['unit'],
                )

                if ingredient_obj and self._needs_nutrition_completion(item.get('nutrition') or {}):
                    NutritionDataFiller.fill_missing_ingredient_nutrition(
                        ingredient_obj,
                        use_spoonacular=True,
                        use_gemini=True,
                    )

                if created:
                    ingredients_created += 1
                else:
                    ingredients_updated += 1

            if i % 50 == 0:
                self.stdout.write(
                    f'  ✓ {i}/{len(data)} | Foods new: {foods_created} upd: {foods_updated}'
                    f' | Ingredients new: {ingredients_created} upd: {ingredients_updated}'
                )

        # --- Summary ----------------------------------------------------------
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('SAVE COMPLETE'))
        self.stdout.write(f'  Foods created       : {foods_created}')
        self.stdout.write(f'  Foods updated       : {foods_updated}')
        self.stdout.write(f'  Ingredients created : {ingredients_created}')
        self.stdout.write(f'  Ingredients updated : {ingredients_updated}')
        self.stdout.write(f'  Total items         : {len(data)}')
        self.stdout.write('=' * 80)
        if spoonacular_disabled_reason:
            self.stdout.write(self.style.WARNING(f'  Note: {spoonacular_disabled_reason}'))

    # -------------------------------------------------------------------------
    # Scheduler / execute wrappers
    # -------------------------------------------------------------------------

    def execute_crawl(self, limit_categories=None, limit_items=None):
        self.stdout.write(self.style.SUCCESS('Scheduled crawl starting...'))
        self.ensure_target_categories(limit_categories=limit_categories)
        self.crawl(limit_categories=limit_categories, limit_items=limit_items)
        # After all targets, compact Food and Ingredient IDs to be sequential
        self.resequence_food_ids()
        self.resequence_ingredient_ids()
        self.stdout.write(self.style.SUCCESS('OK Scheduled crawl complete'))

    def run_scheduler(self, limit_categories=None, limit_items=None):
        if schedule is None:
            raise RuntimeError('schedule package chua duoc cai dat; khong the chay --schedule')

        schedule.every().day.at('00:00').do(
            self.execute_crawl, limit_categories=limit_categories, limit_items=limit_items
        )
        schedule.every().day.at('12:00').do(
            self.execute_crawl, limit_categories=limit_categories, limit_items=limit_items
        )

        self.stdout.write(self.style.SUCCESS('Crawler scheduler started.'))
        self.stdout.write(self.style.SUCCESS('Next runs: 00:00 and 12:00 every day.'))
        self.stdout.write(self.style.WARNING('Keep this process running to execute scheduled crawls.'))

        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nCrawler scheduler stopped by user.'))

    # -------------------------------------------------------------------------
    # Entry point
    # -------------------------------------------------------------------------

    def handle(self, *args, **options):
        try:
            limit_categories      = options.get('limit_categories')
            limit_items           = options.get('limit_items')
            reset_ingredients     = options.get('reset_ingredients_before_crawl')
            compact_category_ids  = options.get('compact_category_ids')
            prepare_categories_only = options.get('prepare_categories_only')
            schedule_mode         = options.get('schedule')

            self.stdout.write(self.style.SUCCESS(
                'Crawl targets are mapped from requested WinMart URLs (slug + cate2).'
            ))

            if schedule_mode:
                self.run_scheduler(limit_categories=limit_categories, limit_items=limit_items)
                return

            # --- Pre-crawl maintenance ---
            self.deduplicate_target_categories(limit_categories=limit_categories)
            self.ensure_target_categories(limit_categories=limit_categories)
            if compact_category_ids:
                self.compact_category_ids(limit_categories=limit_categories)

            if prepare_categories_only:
                self.stdout.write(self.style.SUCCESS('OK categories prepared only'))
                return

            spoon_error = get_spoonacular_last_error()
            if spoon_error:
                self.stdout.write(self.style.WARNING(f'Spoonacular note: {spoon_error}'))

            # --- Optional reset before crawl (not default to prevent accidental data loss) ---
            if reset_ingredients:
                self.clear_ingredients_before_crawl()

            # --- Crawl & save ---
            self.crawl(limit_categories=limit_categories, limit_items=limit_items)

            # --- Post-crawl: resequence Ingredient IDs to be 1, 2, 3 ... ---
            self.resequence_ingredient_ids()
            self.resequence_food_ids()
            
            # --- Verify data integrity: remove orphans, check duplicates ---
            self.verify_ingredient_data_integrity()

            self.stdout.write(self.style.SUCCESS('\nOK crawl complete'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            raise
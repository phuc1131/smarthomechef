# AI Model - Smart Home Chef

Tai lieu nay la ban tong hop day du ve toan bo he thong AI, trainning va ca nhan hoa dang duoc phat trien trong du an.

Muc tieu cua file:
- Mo ta dung hien trang code, khong dua tren tai lieu cu.
- Giai thich tu kien truc, model, du lieu, quy trinh train/cap nhat, den van hanh.
- Lam ro cac phan dang chay on dinh va cac phan dang phat trien tiep.

---

## 1. Tong Quan He AI Trong Du An

He AI cua Smart Home Chef khong phai mot model don le, ma la he thong lai (hybrid):
- Rule-based NLU + intent mapping.
- LLM generation (Gemini) cho nhung bai toan can suy luan/ngon ngu tu do.
- Similarity cache de tai su dung cau tra loi.
- Heuristic engine cho food/ingredient classification va fallback.
- Data models cho recommendation va personalization.

Muc tieu san pham:
- Tu van noi tro va dinh duong bang tieng Viet.
- Goi y mon an, meal plan, recipe, bien tau cong thuc.
- Tich luy hanh vi de ca nhan hoa de xuat.

---

## 1. Co So Ly Thuyet Ve Tri Tue Nhan Tao

Phan nay tom tat cac co so ly thuyet can thiet de giai thich cach he thong ung dung AI vao bai toan goi y dinh duong va lap thuc don.

### 1.1. Tri tue nhan tao (Artificial Intelligence)

Tri tue nhan tao la linh vuc nghien cuu cac he thong co kha nang mo phong mot so hoat dong thong minh cua con nguoi nhu nhan biet, suy luan, hoc tu du lieu, va dua ra quyet dinh. Trong bai toan lap thuc don, AI duoc dung de:
- Phan tich yeu cau nguoi dung.
- Goi y mon an phu hop voi muc tieu suc khoe.
- Sinh noi dung tu nhien cho chat bot va giai thich khuyen nghi.

### 1.2. Hoc may (Machine Learning)

Hoc may la tap con cua AI, cho phep he thong rut ra quy luat tu du lieu lich su ma khong can lap trinh thu cong tung truong hop. Trong he thong nay, hoc may duoc ap dung de:
- Phan loai y dinh nguoi dung.
- Xep hang mon an theo do phu hop.
- Hoc tu hanh vi click, luu, bo qua, danh gia cua nguoi dung.

### 1.3. Xu ly ngon ngu tu nhien (Natural Language Processing - NLP)

NLP giup may tinh hieu van ban tu nhien cua con nguoi. Ung dung trong du an bao gom:
- Hieu cau hoi cua nguoi dung ve dinh duong va thuc don.
- Trich xuat nguyen lieu, mon an, khau phan tu doan van.
- Sinh cau tra loi tu nhien bang tieng Viet.

### 1.4. He goi y (Recommender System)

He goi y la ky thuat dua ra danh sach doi tuong phu hop nhat cho tung nguoi dung dua tren du lieu va hanh vi. Voi bai toan thuc don, he goi y can xem xet:
- So thich va so truong ca nhan.
- Lich su an uong.
- Ngans sach.
- Benh ly va ranh buoc dinh duong.

### 1.5. Hoc sau (Deep Learning)

Hoc sau la mot phuong phap hoc may nang cao dung mang noron nhieu lop de nhan dien mau phuc tap. Trong he thong nay, hoc sau co the duoc su dung trong cac bai toan:
- Hieu ngon ngu tu nhien phuc tap.
- Trich xuat y nghia tu text.
- Nang cap bo phan phan loai y dinh hoac sinh cau tra loi.

### 1.6. He thong lai (Hybrid AI)

He thong lai ket hop nhieu ky thuat nhu rule-based, hoc may, va LLM de tang do on dinh va do chinh xac. Day la mo hinh phu hop nhat cho bai toan lap thuc don vi:
- Rule-based dam bao cac rang buoc cung nhu benh ly, ngan sach, va calories.
- Hoc may dung de xep hang va ca nhan hoa.
- LLM (Gemini) dung de sinh noi dung va fallback khi du lieu noi bo chua du.

### 1.7. Ca nhan hoa dua tren hanh vi nguoi dung

Ca nhan hoa la qua trinh dieu chinh ket qua dua tren du lieu rieng cua tung nguoi dung. Trong he thong goi y thuc don, ca nhan hoa duoc tao ra tu:
- Ho so suc khoe.
- Muc tieu giam can, tang co, duy tri can nang.
- Lich su an uong.
- Danh gia va phan hoi cua nguoi dung.

### 1.8. Vong phan hoi (Feedback Loop)

Feedback loop la co che dung ket qua tuong tac cua nguoi dung de cap nhat lai he thong. Neu nguoi dung chon mot mon, he thong tang trong so cho dac trung tuong ung. Neu nguoi dung bo qua, he thong co the giam diem phu hop cua mon do.

### 1.9. Bo loc rang buoc va xep hang

Bai toan thuc don khong chi la tim mon co diem cao nhat ma con phai ton trong rang buoc cung. Vi vay can ket hop:
- Bo loc rang buoc de loai bo mon khong phu hop.
- Bo xep hang de chon ra mon tot nhat trong tap ung vien con lai.

### 1.10. Ung dung vao he thong Smart Home Chef

Tu co so ly thuyet tren, he thong duoc thiet ke theo huong:
- Quan ly du lieu nguoi dung va du lieu dinh duong trong co so du lieu.
- Tinh diem phu hop cho tung mon an dua tren cong thuc ca nhan hoa.
- Dung AI de ho tro suy luan, sinh goi y va fallback khi can.
- Luu lai phan hoi nguoi dung de cai tien ket qua trong cac lan de xuat tiep theo.

---

## 2. Kien Truc AI Hien Tai

### 2.1 Lop Inference (thoi gian thuc)

1) Chat AI:
- Nhan tin nhan user.
- Intent classification nhanh bang keyword.
- Tim ket qua DB/cache truoc.
- Neu can thi goi Gemini.

2) Ingredient parsing:
- Uu tien Gemini trich xuat nguyen lieu tu text tu nhien.
- Neu loi thi fallback keyword matching.

3) Recipe recommendation:
- Uu tien tim mon trong DB dua tren ingredient matching.
- Neu khong du ket qua thi goi Gemini.
- Neu Gemini loi thi fallback hardcoded recipes.

4) Meal plan generation:
- Uu tien data trong DB + profile user.
- Neu DB khong du thi fallback sang Gemini de de xuat mon.

### 2.2 Lop Du Lieu Hoc va Ca Nhan Hoa

- Chat history: ChatSession, ChatMessage.
- Nhan intent: MessageIntent, Pattern, Intent.
- Embedding store: IntentEmbedding.
- Cache LLM response: ChatResponseCache.
- Recommendation learning models: MealRecommendation, UserFeedbackRecommendation, RecommendationLog, ModelMetadata.
- User personalization models: UserBudget, UserHealthGoal.

### 2.3 Lop Enrichment tu API ngoai

- Gemini: sinh text, dich, parse JSON theo prompt.
- Spoonacular/TheMealDB: bo sung du lieu food/recipe.

---

## 3. Cac Model/Engine AI Dang Co

## 3.1 Gemini LLM Engine

Vai tro:
- Chat response generation.
- Ingredient extraction.
- Recipe list generation.
- Recipe detail generation.
- Recipe variation generation.
- Meal plan fallback generation.
- Dich noi dung recipe sang tieng Viet.

Cau hinh:
- GEMINI_API_KEY
- GEMINI_MODEL (mac dinh: gemini-2.5-flash)
- GEMINI_BASE_URL (optional)
- GEMINI_ENABLED

Hanh vi quan trong:
- Neu AI unavailable thi fallback an toan ve DB/rule message.
- Prompt thuong yeu cau output JSON de parser de xu ly.
- Co co che quota fallback neu gap loi 429/RESOURCE_EXHAUSTED.

File lien quan:
- app/config.py
- app/services/external_apis.py
- app/features/user_panel/views.py

## 3.2 Intent Classification Engine (Rule-based + data labels)

Hien trang:
- classify_intent() trong user_panel/views.py dang dung keyword heuristic.
- Intent labels duoc luu vao MessageIntent.

Cac nhom intent hien dien:
- meal_plan
- nutrition
- general/fallback
- Ngoai ra he thong du lieu co cac intent khac trong bang intent_patterns (health_goal, budget_query, ingredient_query, ...).

Y nghia trainning:
- Moi tin nhan user duoc gan intent la mot mau hoc co nhan.
- Pattern va intent_patterns la tap mau train de nang cap bo phan classifier sau nay.

File lien quan:
- app/features/user_panel/views.py
- apps/chat/models.py
- apps/core_models/ai_learning_models.py
- tools/seeding/seed_data_consolidated.py

## 3.3 Chat Similarity Cache Model

Model logic:
- Chuan hoa query bang tokenize_chat_text().
- Lay top cache entries gan nhat.
- Tinh Jaccard similarity tren token sets.
- Neu similarity >= 0.70 thi reuse response.

Loi ich:
- Giam so lan goi Gemini.
- Tang toc do phan hoi.
- Tao feedback signal thong qua usage_count.

File lien quan:
- app/services/chat_text_service.py
- app/services/external_apis.py
- apps/chat/models.py

### 3.3.3 Thiết kế giải pháp tích hợp AI

Mục tiêu: xác định một giải pháp tích hợp AI an toàn, có thể giám sát, và hiệu quả chi phí cho các use-case: chat response, ingredient parsing, recipe/meal-plan fallback.

Nguyên tắc thiết kế ngắn gọn:
- DB-first: luôn ưu tiên dữ liệu nội bộ; gọi LLM chỉ khi cần (fallback, sáng tạo, giải thích).
- Validate-first: mọi output AI phải qua kiểm tra schema và hard-constraints trước khi dùng.
- Cache & debounce: giảm tần suất gọi LLM bằng cache có TTL và nhóm requests tương tự.
- Least-privilege: không đưa PII/medical details nhạy cảm vào prompt; truyền tóm tắt an toàn.

Kiến trúc high-level:
- `AIOrchestrator` (entrypoint): quyết định capability nào cần (intent, personalization, generation), chọn backend (db, cache, gemini), và phối hợp các bước validate/cache.
- `PromptBuilder`: sinh prompt template, inject only safe summary of user context.
- `GeminiAdapter` (`external_apis.py`): wrapper gọi model, xử lý retry, rate-limit, parse JSON, lưu raw_response_id.
- `Validator`: schema check + business-rule check (allergy, budget, nutrition sanity).
- `RecommendationSink`: lưu `AIRecommendation` + reason + model_version; emit metrics.

Luồng dữ liệu (tổng quát):
1. Request từ user -> `AIOrchestrator`.
2. `AIOrchestrator` gọi các service nội bộ (cache, personalization) để tìm candidate.
3. Nếu cần AI, `PromptBuilder` tạo prompt có structure và `GeminiAdapter` gọi LLM.
4. `Validator` kiểm tra output; nếu pass -> `RecommendationSink` lưu và trả về cho user; nếu fail -> fallback rule hoặc lỗi có message an toàn.

Prompt & schema:
- Yêu cầu output JSON with explicit keys (e.g., {"items": [{"name":"...","reason":"...","calories":...}]}) để dễ parse.
- Hạn chế độ dài prompt; tóm tắt context: goal, allergies (cụ thể), budget band, recent_food_ids (IDs hoặc normalized names).

Caching & rate-limiting:
- Cache key gồm hash(prompt_template + user_profile_summary). TTL configurable (e.g., 12h cho meal-plan suggestions, 1h cho chat responses).
- Throttle per-account + global rate-limits; fallback to cached response or rule engine when quota exceeded.

Validation & safety checks:
- Schema validation (JSON parse + required fields).
- Business validation: hard-constraint check (allergy, disease, budget), numeric sanity (calories within plausible range), duplicates removal.
- If any check fails, record failure reason and attempt automated repair (e.g., remove offending ingredient) or return safe fallback.

Monitoring & metrics:
- Track: calls count, latency, success_rate, parse_failures, validation_failures, token_usage, cost per request.
- Log raw_response_id only (truncated) and link to `AIRecommendation` for audit; redact PII in stored prompts.

Operational checklist before production:
1. Confirm `GEMINI_ENABLED` and secure `GEMINI_API_KEY` in `app/config.py`.
2. Add schema definitions and validators used by `Validator`.
3. Implement caching layer and backoff policies in `external_apis.py`.
4. Add metrics instrumentation around `AIOrchestrator` and `GeminiAdapter`.
5. Run integration tests simulating quota errors, invalid AI outputs, and validate fallbacks.

```mermaid
flowchart LR
	U[User request / Chat / Meal-plan request] --> ORC[AIOrchestrator]
	ORC --> DBCHK{Check DB / Cache / Personalization}
	DBCHK -- Enough candidates --> RANK[Rank & Return Recommendations]
	DBCHK -- Not enough / Low score --> PROMPT[PromptBuilder: build safe prompt]
	PROMPT --> GEM[GeminiAdapter (call LLM)]
	GEM --> RAW[Raw response (store raw_response_id)]
	RAW --> VAL[Validator: schema & business rules]
	VAL -- Pass --> SINK[RecommendationSink: save AIRecommendation + metrics]
	SINK --> RESP[Return recommendations to user]
	VAL -- Fail --> FB[Fallback Rule Engine]
	FB --> RESP
	RANK --> RESP
	RESP --> LOG[Log: SearchEvent / user feedback]
	RESP --> METRICS[Emit metrics: latency, cost, parse_failures]
	ORC -->|Throttle/Rate-limit| RATE[Rate-limiter & Cache]
	RATE --> DBCHK
```


## 3.4 Ingredient Parser Model

Pipeline:
1. Nhan text user.
2. Goi Gemini de trich xuat JSON array ingredients.
3. Chuan hoa ten ingredient qua alias map va IngredientAlias DB.
4. Remove duplicates, giu thu tu.
5. Neu Gemini fail: fallback keyword extraction.

Output co confidence + method:
- method: gemini | fallback | error.

File lien quan:
- app/services/ingredient_parser_service.py

## 3.5 Recipe Recommendation Model

Pipeline:
1. Chuan hoa ingredient keywords.
2. Tim foods tu DB theo FoodIngredient mapping.
3. Cham diem mon theo:
- so nguyen lieu thieu
- do kho
- confidence
4. Neu DB khong co -> goi Gemini.
5. Neu Gemini fail -> fallback recipe templates.

Co bo check incompatibility matrix de canh bao ket hop nguyen lieu bat hop ly.

File lien quan:
- app/services/recipe_generator_service.py

## 3.6 Recipe Variation Model

Muc tieu:
- Xu ly truong hop thieu nguyen lieu.

Pipeline:
1. Phan loai nguyen lieu thieu: essential/important/optional.
2. De xuat thay the tu dictionary.
3. Tao bien tau rule-based.
4. Neu co Gemini thi sinh them bien tau sang tao.

File lien quan:
- app/services/recipe_variations_service.py

## 3.7 Meal Plan Generator Model

Muc tieu:
- Tao meal plan theo profile, benh ly, muc tieu va ngan sach.

Pipeline:
1. analyze_request() de phan loai yeu cau (health/budget/diet/general).
2. get_user_context() lay profile + goals + diseases + preferences + lich su an gan day.
3. build_food_filter() tao Q filters ca nhan hoa.
4. query_foods_from_db() lay mon theo tung bua.
5. tinh servings theo target calories cua bua.
6. tao MealPlan records.
7. Neu DB khong du -> generate_meal_plan_with_gemini().

### 3.7.1 Flowchart: Thuật toán phân tích dữ liệu & cá nhân hoá thực đơn

```mermaid
flowchart LR
	Start[Start: request for meal-plan / recommendation] --> CTX[Build user context\n(profile, goals, history, budget)]
	CTX --> FEAT[Feature extraction\ncalorie_ratio, protein_density,\npref_match, budget_fit, variety, q]
	FEAT --> FILTER[Hard-constraint Filter\n(allergies, disease, explicit avoids, budget hard-limit)]
	FILTER -- Reject -> REJ[Reject/Ask user for input]
	FILTER -- Pass -> SCORE[Compute Z(u,f)\nweighted sum of features]
	SCORE --> SIG[Apply sigmoid S(u,f)]
	SIG --> RANK[Sort by score desc]
	RANK --> DIVER[Re-rank for diversity\npenalize similarity]
	DIVER --> CHECK{Enough & max_score >= θ?}
	CHECK -- Yes --> SELECT[Select top items\nadjust servings to meet meal calories]
	CHECK -- No --> CALLAI[Call AI fallback\n(generate candidates)]
	CALLAI --> VALID_AI[Validate AI outputs]
	VALID_AI -- Pass --> SELECT
	VALID_AI -- Fail --> FALLBACK2[Fallback rule-based selection]
	SELECT --> SAVE[Save MealPlan entries\nlog AIRecommendation (if AI used)]
	SAVE --> FEEDBACK[Collect user feedback\n(accept/reject/rating)]
	FEEDBACK --> UPDATE[Update weights / store training tuple]
	UPDATE --> End[End]
```

File lien quan:
- app/services/meal_plan_generator_service.py

## 3.8 Food Classifier Engine

Muc tieu:
- Phan biet ingredient vs food dua tren keyword + profile dinh duong.

Heuristic:
- ingredient: thuong khong co calories/macros day du.
- food: co calories + macros.

Phuc vu cho data cleaning va nutrition fill process.

File lien quan:
- app/services/food_classifier_service.py
- app/services/nutrition_data_service.py

---

## 4. Mo Hinh Du Lieu Phuc Vu AI va Trainning

## 4.1 Chat + NLU tables

1) intents
- Danh sach intent.

2) patterns
- Mau cau gan voi intent.

3) chat_sessions
- Context cua phien chat.

4) chat_messages
- Lich su hoi thoai user/assistant.

5) message_intents
- Nhan intent cho tung user message.

6) intent_embeddings
- Luu vector embedding cho message/pattern (ha tang de nang cap classifier semantic).

7) chat_response_caches
- Cache response + usage_count.

File model:
- apps/chat/models.py

## 4.2 Recommendation + Learning tables

1) meal_recommendations
- Goi y mon cho user va cac score (overall/match/budget/health).

2) user_feedback_food
- Rating/like/dislike tren food.

3) user_feedback_recommendation
- Phan hoi user ve recommendation cua AI.

4) intent_patterns
- Pattern huan luyen bo sung cho classifier.

5) recommendation_log
- Log de xuat va model_version.

6) model_metadata
- Metadata version model.

File model:
- apps/core_models/ai_learning_models.py

## 4.3 Personalization tables

1) user_budgets
- Ngan sach theo chu ky (daily/weekly/monthly).

2) user_health_goals
- Muc tieu suc khoe + target macros.

File model:
- apps/users/personalization_models.py

---

## 5. Quy Trinh Trainning va Cap Nhat Du Lieu

Luu y quan trong:
- He thong hien tai theo huong data-centric trainning, chua co script offline train neural classifier PyTorch dang duoc su dung trong code runtime.
- Tai lieu cu co de cap train_intent_embeddings va artifacts .pt/.json nhung khong con thay trong code hien hanh.

## 5.1 Quy trinh trainning data intent

Buoc 1: Seed intent va pattern co ban.

Command:
```powershell
python tools/seeding/seed_data_consolidated.py --intents
python tools/seeding/seed_data_consolidated.py --patterns
```

Buoc 2: Thu thap chat that.
- chat_send tao ChatMessage.
- classify_intent tao MessageIntent.

Buoc 3: Curate patterns.
- Admin bo sung/duyet patterns trong intents/patterns hoac intent_patterns.

Buoc 4: Danh gia chat logs.
- Theo doi mismatch intent va cap nhat pattern.

## 5.2 Quy trinh trainning personalization

Buoc 1: Khoi tao budget/goal mac dinh cho user active.

Command:
```powershell
python manage.py backfill_personalization
```

Buoc 2: Tao recommendation records ban dau.
- MealRecommendation duoc tao tu du lieu recipe/food.

Buoc 3: Thu feedback user.
- UserFeedbackFood
- UserFeedbackRecommendation

Buoc 4: Tinh diem goi y moi (v2/v3 roadmap).

## 5.3 Quy trinh trainning du lieu food/nutrition

Buoc 1: Thu data qua crawl/API search.
Buoc 2: Fill nutrition qua Spoonacular service.
Buoc 3: Validate bang NutritionDataValidator.
Buoc 4: Chuan hoa ingredient alias.

---

## 6. Quy Trinh AI End-to-End Theo Nghiep Vu

## 6.1 Chat pipeline

1. API chat_send nhan message.
2. Save user message vao chat_messages.
3. classify_intent() gan nhan nhanh.
4. Thu auto meal plan/hardcoded/database search.
5. Thu saved answer va similarity cache.
6. Neu can thi goi Gemini qua call_gemini_with_debug().
7. Cache response thanh cong vao chat_response_caches.
8. Save assistant message.
9. Cap nhat user preference profile.

File chinh:
- app/features/user_panel/views.py

## 6.2 Ingredient -> Recipe pipeline

1. ai_parse_ingredients -> parse_ingredients_from_text().
2. ai_recommend_recipes -> recommend_recipes_from_ingredients().
3. ai_generate_recipe -> generate_recipe_details().
4. ai_recipe_variations -> generate_recipe_variations().

File chinh:
- app/features/user_panel/views.py
- app/services/ingredient_parser_service.py
- app/services/recipe_generator_service.py
- app/services/recipe_variations_service.py

## 6.3 Meal plan pipeline

1. Nhan request meal plan.
2. Analyze request type.
3. Lay user context + preferences.
4. Query mon tu DB theo filter ca nhan hoa.
5. Tao plan theo tung bua va servings.
6. Neu khong du du lieu: fallback Gemini.

File chinh:
- app/services/meal_plan_generator_service.py

---

## 7. API AI Dang Duoc Expose

Trong user panel views dang co cac endpoint AI:
- POST ai_parse_ingredients
- POST ai_recommend_recipes
- POST ai_generate_recipe
- POST ai_recipe_variations
- chat_send (chat AI tong hop)

Vai tro:
- Cung cap nang luc AI truc tiep cho UI/agent flow.

---

## 8. Cau Hinh Moi Truong Can Co

## 8.1 Gemini
- GEMINI_API_KEY
- GEMINI_MODEL
- AI_INTEGRATIONS_GEMINI_BASE_URL (optional)

## 8.2 Spoonacular
- SPOONACULAR_API_KEY
- SPOONACULAR_BASE_URL (optional)
- SPOONACULAR_TIMEOUT

## 8.3 Feature flags
- REQUIRE_AUTH
- THEMEALDB_AUTO_TRANSLATE

File cau hinh:
- app/config.py

---

## 9. Van Hanh va Kiem Tra Chat Luong

## 9.1 Checklist sau moi dot cap nhat AI

1. Chay Django check:
```powershell
python manage.py check
```

2. Kiem tra chat basic:
- Cac case meal_plan / nutrition / general.

3. Kiem tra similarity cache:
- Gui 2 cau hoi tuong tu, xac nhan usage_count tang.

4. Kiem tra fallback:
- Gia lap mat GEMINI_API_KEY de dam bao he thong khong crash.

5. Kiem tra ingredient/recipe endpoints:
- parse -> recommend -> detail -> variation.

## 9.2 Metrics nen theo doi

- Cache hit ratio (chat_response_caches reuse).
- Ty le fallback Gemini trong meal plan.
- Ty le parse ingredient thanh cong bang Gemini vs fallback.
- Average response latency chat.
- User acceptance rate cho recommendations.

---

## 10. Cac Thanh Phan Dang Phat Trien (AI Ca Nhan)

1) Personalization scoring nang cao:
- Nang cap MealRecommendation score bang feedback loop thuc te.

2) Feedback-aware reranking:
- Dung UserFeedbackFood + UserFeedbackRecommendation de rerank mon.

3) Intent classifier nang cap semantic:
- Tan dung intent_embeddings de bo sung semantic matching, giam phu thuoc keyword.

4) Model version governance:
- Ghi model_metadata va recommendation_log de co the audit model behavior.

5) Data quality automation:
- Tu dong phat hien sample mau thuan, duplicate patterns, va low-confidence intents.

---

## 11. Luu Y Ky Thuat Quan Trong

1. Tai lieu cu ve PyTorch artifacts/command train_intent_embeddings dang khong dong bo voi code runtime hien tai.
2. Mot so script backfill cu va moi co khac biet duong import model; can doi chieu schema truoc khi chay tren production data.
3. He thong hien dang theo chien luoc "DB-first, AI-fallback" de toi uu quota va do on dinh.
4. Cac service AI duoc thiet ke fail-safe: loi AI se tra fallback thay vi lam crash request.

---

## 12. Lenh Huu Ich Cho Vong Doi AI/Data

Seed du lieu nen:
```powershell
python tools/seeding/seed_data_consolidated.py
```

Seed rieng intents/patterns:
```powershell
python tools/seeding/seed_data_consolidated.py --intents
python tools/seeding/seed_data_consolidated.py --patterns
```

Backfill personalization:
```powershell
python manage.py backfill_personalization
```

Kiem tra he thong:
```powershell
python manage.py check
```

---

## 13. Tom Tat Nhanh

- He AI hien tai la hybrid, khong phu thuoc mot model train offline duy nhat.
- Gemini dong vai tro LLM trung tam cho generation/extraction, nhung luon co fallback.
- Trainning trong giai doan nay tap trung vao data labels, patterns, feedback va recommendation logs.
- AI ca nhan dang phat trien dua tren budget + health goals + behavior feedback.
- Huong di tiep theo la semantic intent matching, reranking recommendation, va model governance ro rang hon.
from django.db import models
from django.utils import timezone


class Intent(models.Model):
    #     Mô hình ý định/chủ đề hội thoại trong chatbot.
#     Dùng để phân loại tin nhắn người dùng thành các chủ đề (recommendation, nutrition, meal_plan, general, v.v.).
#     
#     Ví dụ:
#     - name='recommendation': Người dùng muốn gợi ý đồ ăn
#     - name='nutrition': Người dùng hỏi về dinh dưỡng
#     - name='meal_plan': Người dùng muốn lập kế hoạch ăn
#     
#     Trường:
#     - name: Tên intent duy nhất (ví dụ: 'recommendation')
#     - description: Mô tả ý định (để giúp admin hiểu)
#     - required_fields: JSON danh sách trường bắt buộc để thực hiện ý định
#       Ví dụ: {'recommendation': ['dietary_preference', 'activity_level']}
#     - topic: Chủ đề kỹ thuật (để nhóm các intent liên quan)
#     
#     GHI NHỚ:
#     - Intent phải được tạo sẵn (không auto-generate)
#     - classify_intent() dùng intent name để match keyword/pattern
#     - _predict_intent_from_saved_samples() tra cứu qua MessageIntent table
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    required_fields = models.JSONField(null=True, blank=True)
    topic = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'intents'

    def __str__(self):
        return self.name or f'Intent #{self.pk}'


class Pattern(models.Model):
    #     Mô hình lưu trữ các mẫu câu văn/cụm từ khóa cho mỗi Intent.
#     Dùng để training/matching trong phân loại ý định.
#     
#     Ví dụ cho intent 'nutrition':
#     - "tôi cần bao nhiêu calo"
#     - "hôm nay tôi ăn bao nhiêu protein"
#     - "dinh dưỡng hôm nay như thế nào"
#     
#     Trường:
#     - intent: Link đến Intent
#     - text: Mẫu câu/cụm từ (ví dụ trên)
#     
#     GHI NHỚ:
#     - _predict_intent_from_saved_samples() lấy top 200 pattern gần đây để so khớp
#     - Mỗi pattern được tokenize rồi so Jaccard similarity với tin nhắn user
#     - Pattern từ 'user' messages trong ChatMessage được backfill tự động
    id = models.AutoField(primary_key=True)
    intent = models.ForeignKey(Intent, on_delete=models.CASCADE, db_column='intent_id', null=True, blank=True)
    text = models.TextField()

    class Meta:
        db_table = 'patterns'

    def __str__(self):
        return self.text[:60]


class ChatSession(models.Model):
    #     Mô hình một phiên trò chuyện (session) giữa user và chatbot.
#     Một account có thể có nhiều chat sessions.
#     
#     Trường:
#     - account: Người dùng
#     - title: Tiêu đề phiên (ví dụ: 'Tư vấn dinh dưỡng hôm nay')
#     - created_at: Thời điểm tạo phiên
#     
#     GHI NHỚ:
#     - Xóa session sẽ cascade xóa tất cả ChatMessage trong session
#     - get_chat_session() lấy phiên gần nhất hoặc tạo mới
    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id', null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    # Fields from ConversationState (consolidated)
    missing_fields = models.JSONField(null=True, blank=True, help_text='List of missing fields for current intent')
    ask_count = models.IntegerField(default=0, help_text='Number of questions asked')
    current_intent_id = models.IntegerField(null=True, blank=True, help_text='Current intent being processed')
    filled_fields = models.JSONField(null=True, blank=True, help_text='Fields that have been filled')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_sessions'

    def __str__(self):
        return self.title or f'Session #{self.pk}'


class ChatMessage(models.Model):
    #     Mô hình lưu trữ từng tin nhắn trong cuộc trò chuyện.
#     Đây là dữ liệu tâm của hệ thống learning: mỗi tin nhắn user có thể được:
#     1. Phân loại intent (via MessageIntent)
#     2. Encode thành embedding (via IntentEmbedding)
#     3. Dùng làm mẫu training cho similarity matching
#     
#     Trường:
#     - session: Link đến ChatSession
#     - role: 'user' hoặc 'assistant' (ai gửi tin nhắn)
#     - content: Nội dung tin nhắn
#     - created_at: Thời điểm gửi (sắp xếp mặc định)
#     
#     GHI NHỚ QUAN TRỌNG:
#     - _backfill_chat_intents_from_history() scan tin nhắn 'user' chưa label
#     - _predict_intent_from_saved_samples() dùng 400 tin nhắn user gần nhất
#     - Xóa session sẽ xóa tất cả messages (CASCADE)
#     - Để enable learning, luôn cần có lịch sử messages
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, db_column='session_id', null=True, blank=True)
    role = models.CharField(max_length=50)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class ChatSummary(models.Model):
    #     Mô hình tóm tắt tự động một phiên chat.
#     Có thể được tạo bằng AI (Gemini API) hoặc tính toán thủ công.
#     
#     Trường:
#     - session: Link đến ChatSession
#     - summary: Nội dung tóm tắt
#     - created_at: Thời điểm tạo tóm tắt
#     
#     GHI NHỚ:
#     - Chưa implement đầy đủ, có thể thêm task background để auto-summarize
    session = models.ForeignKey(ChatSession, on_delete=models.DO_NOTHING, db_column='session_id', null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_summaries'


class MessageIntent(models.Model):
    #     Mô hình liên kết giữa ChatMessage và Intent (phân loại ý định).
#     Mỗi tin nhắn 'user' được gắn nhãn với một intent có độ tin cậy nhất định.
#     
#     Trường:
#     - message: Link đến ChatMessage
#     - intent: Link đến Intent (phân loại)
#     - confidence: Độ tin cậy của phân loại (0.0 - 1.0)
#     
#     Luồng hoạt động:
#     1. User gửi tin nhắn chat_send()
#     2. classify_intent() phân loại ý định (keyword/embedding/jaccard)
#     3. Tạo MessageIntent mới với intent + confidence
#     4. Lần sau _predict_intent_from_saved_samples() dùng entry này để match
#     
#     GHI NHỚ QUAN TRỌNG:
#     - Đây là nơi hệ thống "học" từ dữ liệu: mỗi tin nhắn được classify tạo training signal
#     - Nếu không có MessageIntent, sẽ dùng Pattern table hoặc keyword fallback
#     - _backfill_chat_intents_from_history() tạo MessageIntent cho tin cũ
#     - Để improve accuracy: thêm rule hoặc pattern khi phân loại sai
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, db_column='message_id', null=True, blank=True)
    intent = models.ForeignKey(Intent, on_delete=models.CASCADE, db_column='intent_id', null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'message_intents'


class IntentEmbedding(models.Model):
    # Tin nhắn hoặc mẫu được encode thành embedding vector
    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        db_column='message_id',
        null=True,
        blank=True,
    )
    # Nếu không phải từ message, có thể từ Pattern hoặc intent keyword
    pattern = models.OneToOneField(
        Pattern,
        on_delete=models.CASCADE,
        db_column='pattern_id',
        null=True,
        blank=True,
    )
    
    # Tên intent được gắn nhãn
    intent_name = models.CharField(max_length=100, null=True, blank=True)
    
    # Vector embedding dưới dạng JSON (chuỗi số float)
    # Thường là 384 hoặc 768 chiều tùy vào mô hình
    embedding_vector = models.JSONField()
    
    # Thông tin metadata: nguồn dữ liệu, độ tin cậy
    source_type = models.CharField(
        max_length=20,
        choices=[('chat', 'Chat Message'), ('pattern', 'Pattern'), ('keyword', 'Intent Keyword')],
        default='chat'
    )
    confidence = models.FloatField(null=True, blank=True)
    
    # Timestamp để theo dõi khi nào được tạo/cập nhật
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intent_embeddings'
        indexes = [
            models.Index(fields=['intent_name', 'source_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.intent_name} - {self.source_type}"


class ChatResponseCache(models.Model):
    #     Mô hình cache các câu trả lời từ Gemini API để tránh gọi API lặp lại.
#     
#     Chiến lược cache cải thiện:
#     1. Khi user gửi câu hỏi mới, phân loại intent trước
#     2. Tìm cache trong nhóm intent đó, dùng similarity >= threshold (0.75+)
#     3. Nếu intent không match, dùng fallback general cache
#     4. Nếu không có cache, gọi Gemini API và lưu vào cache với intent_name
#     
#     Trường:
#     - normalized_query: Câu hỏi sau khi normalize (lowercase, remove punct, lemmatize)
#     - original_query: Câu hỏi gốc từ user (để reference)
#     - response: Câu trả lời từ Gemini API
#     - intent_name: Intent của câu hỏi (meal_plan, nutrition, recipe, vv) để group cache
#     - usage_count: Số lần response này được reuse (metrics)
#     - created_at: Thời điểm tạo cache
#     
#     GHI NHỚ:
#     - Được tạo sau khi Gemini trả lời thành công
#     - intent_name giúp matching tập trung vào intent tương tự (tăng độ chính xác)
#     - Cleanup task nên xóa entries cũ (>30 days) để giữ DB size manageable
#     - Similarity threshold nên tunable via settings (hiện tại 0.75)
    normalized_query = models.TextField(help_text='Query sau khi normalize (lowercase, remove punct, lemmatize)')
    original_query = models.TextField(help_text='Query gốc từ user')
    response = models.TextField(null=True, blank=True, help_text='Full response từ Gemini API')
    intent_name = models.CharField(max_length=100, null=True, blank=True, help_text='Intent của câu hỏi (meal_plan, nutrition, recipe, recommendation, vv)')
    usage_count = models.IntegerField(default=0, help_text='Số lần response này được reuse (metrics)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_response_caches'
        indexes = [
            models.Index(fields=['normalized_query']),
            models.Index(fields=['intent_name', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        query_preview = self.normalized_query[:50]
        return f"Cache: {query_preview}... (used {self.usage_count}x)"

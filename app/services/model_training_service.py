"""Lightweight internal AI training service.

Module này xây dựng một bộ phân loại intent có thể huấn luyện từ chính dữ liệu
của dự án. Mô hình không dùng thư viện ML bên ngoài, nên có thể chạy trực tiếp
trong stack hiện tại và cải thiện dần từ nhãn chat + pattern được lưu trong DB.
"""

# Cho phép dùng annotation kiểu mới ngay cả khi chạy trên một số phiên bản Python cũ hơn.
from __future__ import annotations

# Dùng để đọc/ghi file JSON chứa snapshot mô hình.
import json
# Dùng để tính toán log probability trong mô hình Naive Bayes.
import math
# Counter dùng để đếm token; defaultdict giúp tự tạo Counter theo từng intent.
from collections import Counter, defaultdict
# dataclass dùng để tạo class lưu kết quả dự đoán gọn hơn.
from dataclasses import dataclass
# timezone chuẩn UTC dùng khi tạo version theo thời gian.
from datetime import timezone
# Path giúp xử lý đường dẫn file/thư mục an toàn, dễ đọc hơn.
from pathlib import Path
# Các kiểu dữ liệu phục vụ type hint cho code rõ ràng hơn.
from typing import Any, Dict, List, Optional, Tuple

# Import timezone của Django để lấy thời gian hiện tại theo cấu hình Django.
from django.utils import timezone as django_timezone

# Import các model liên quan đến chatbot: intent, nhãn intent của message và pattern mẫu.
from apps.chat.models import Intent, MessageIntent, Pattern
# Import model lưu metadata/lịch sử phiên bản mô hình AI đã train.
from apps.core_models.ai_learning_models import ModelMetadata
# Hàm tách văn bản chat thành các token đã chuẩn hóa.
from app.services.chat_text_service import tokenize_chat_text


# Xác định thư mục gốc của project dựa trên vị trí file hiện tại.
BASE_DIR = Path(__file__).resolve().parents[2]
# Thư mục dùng để lưu artifact của mô hình AI nội bộ.
AI_MODEL_DIR = BASE_DIR / 'artifacts' / 'ai_models'
# Đường dẫn file JSON lưu snapshot của mô hình phân loại intent.
INTENT_MODEL_PATH = AI_MODEL_DIR / 'intent_classifier.json'
# Tên cố định của mô hình, dùng khi lưu metadata và tạo version.
MODEL_NAME = 'intent_classifier'


@dataclass(frozen=True)
class IntentPrediction:
    """Class chứa kết quả dự đoán intent cho một câu người dùng nhập vào."""

    # Tên intent dự đoán được; None nếu không đủ tự tin hoặc không có dữ liệu.
    intent_name: Optional[str]
    # Độ tin cậy của intent tốt nhất, nằm trong khoảng 0 -> 1.
    confidence: float
    # Điểm raw/log-score của tất cả intent, dùng để debug hoặc xếp hạng.
    scores: Dict[str, float]
    # Các token trong câu người dùng góp phần làm bằng chứng cho intent dự đoán.
    evidence_tokens: List[str]
    # Phiên bản mô hình đã được dùng để dự đoán.
    model_version: Optional[str]


def _normalize_time_string() -> str:
    """Tạo chuỗi thời gian UTC dạng YYYYMMDDHHMMSS để gắn vào version mô hình."""

    # Lấy thời gian hiện tại của Django, chuyển sang UTC rồi format thành chuỗi ngắn gọn.
    return django_timezone.now().astimezone(timezone.utc).strftime('%Y%m%d%H%M%S')


def _ensure_model_dir() -> None:
    """Đảm bảo thư mục lưu mô hình tồn tại trước khi ghi file."""

    # parents=True: tạo cả thư mục cha nếu chưa có.
    # exist_ok=True: không báo lỗi nếu thư mục đã tồn tại.
    AI_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _tokenize_with_hints(text: str) -> List[str]:
    """Tách văn bản thành token và loại bỏ token rỗng."""

    # tokenize_chat_text là hàm chuẩn hóa/tokenize riêng của hệ thống.
    # List comprehension này chỉ giữ lại các token có giá trị thật.
    return [token for token in tokenize_chat_text(text) if token]


def _intent_hint_tokens(intent: Intent) -> List[str]:
    """Tạo token gợi ý từ thông tin mô tả của một intent."""

    # Ghép tên intent, chủ đề và mô tả để bổ sung thêm dữ liệu nhận diện intent.
    hint_text = ' '.join([
        intent.name or '',
        intent.topic or '',
        intent.description or '',
    ])

    # Nếu intent có required_fields thì đưa các field này vào hint text.
    # Việc này giúp mô hình học thêm các từ khóa liên quan đến dữ liệu bắt buộc của intent.
    if intent.required_fields:
        hint_text += ' ' + ' '.join(map(str, intent.required_fields))

    # Trả về danh sách token đã chuẩn hóa từ phần hint text.
    return _tokenize_with_hints(hint_text)


def _collect_training_documents() -> List[Tuple[str, str, str]]:
    """Thu thập dữ liệu huấn luyện từ Pattern và MessageIntent trong database."""

    # Mỗi document có dạng: (tên intent, nội dung văn bản, nguồn dữ liệu).
    documents: List[Tuple[str, str, str]] = []

    # Lấy các pattern có liên kết với intent hợp lệ.
    # select_related('intent') giúp giảm số query khi truy cập pattern.intent.
    patterns = Pattern.objects.select_related('intent').filter(intent__name__isnull=False)
    for pattern in patterns:
        # Chỉ thêm pattern nếu có intent, tên intent và text đầy đủ.
        if pattern.intent and pattern.intent.name and pattern.text:
            documents.append((pattern.intent.name, pattern.text, 'pattern'))

    # Lấy các message đã được gán nhãn intent.
    # select_related giúp lấy intent và message trong cùng truy vấn join để tối ưu hiệu năng.
    labeled_messages = (
        MessageIntent.objects.select_related('intent', 'message')
        .filter(intent__name__isnull=False, message__content__isnull=False)
    )
    for label in labeled_messages:
        # Chỉ thêm message nếu label đầy đủ intent, message và content.
        if label.intent and label.intent.name and label.message and label.message.content:
            documents.append((label.intent.name, label.message.content, 'message'))

    # Trả về toàn bộ dữ liệu huấn luyện đã gom được.
    return documents


def _load_snapshot_from_disk() -> Optional[Dict[str, Any]]:
    """Đọc snapshot mô hình từ file JSON nếu file đã tồn tại."""

    # Nếu chưa có file mô hình thì trả về None để hệ thống train lại.
    if not INTENT_MODEL_PATH.exists():
        return None
    try:
        # Đọc file JSON và chuyển thành dict Python.
        return json.loads(INTENT_MODEL_PATH.read_text(encoding='utf-8'))
    except Exception:
        # Nếu file lỗi, JSON hỏng hoặc không đọc được thì bỏ qua và cho phép train lại.
        return None


def _save_snapshot_to_disk(snapshot: Dict[str, Any]) -> None:
    """Lưu snapshot mô hình xuống file JSON."""

    # Đảm bảo thư mục lưu mô hình đã tồn tại.
    _ensure_model_dir()
    # ensure_ascii=False giúp giữ tiếng Việt không bị escape.
    # indent=2 giúp file JSON dễ đọc khi mở kiểm tra thủ công.
    INTENT_MODEL_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')


def _update_model_metadata(snapshot: Dict[str, Any]) -> None:
    """Ghi thông tin metadata của lần train mô hình vào database."""

    # Tạo mô tả ngắn về mô hình: tên, số document, số intent và kích thước từ vựng.
    description = (
        f"{snapshot['model_name']} trained with {snapshot['document_count']} documents, "
        f"{snapshot['intent_count']} intents, vocab={snapshot['vocabulary_size']}"
    )

    # Lưu metadata để sau này có thể theo dõi lịch sử train/version của mô hình.
    ModelMetadata.objects.create(
        model_name=snapshot['model_name'],
        version=snapshot['version'],
        description=description,
    )


def train_intent_classifier(force: bool = False) -> Dict[str, Any]:
    """Train mô hình phân loại intent kiểu Naive Bayes từ DB labels và patterns."""

    # Nếu không ép train lại thì ưu tiên dùng snapshot đã lưu trên ổ đĩa.
    if not force:
        existing = _load_snapshot_from_disk()
        if existing:
            return existing

    # Thu thập document huấn luyện từ Pattern và MessageIntent.
    documents = _collect_training_documents()
    # Lấy danh sách intent hợp lệ trong database.
    intents = list(Intent.objects.exclude(name__isnull=True).exclude(name=''))
    # Tạo danh sách tên intent, bỏ các intent không có tên.
    intent_names = [intent.name for intent in intents if intent.name]

    # Lưu số lần xuất hiện của từng token theo từng intent.
    token_counts_by_intent: Dict[str, Counter] = defaultdict(Counter)
    # Lưu số document huấn luyện của từng intent.
    document_count_by_intent: Counter = Counter()
    # Tập từ vựng toàn cục của mô hình.
    vocabulary: set[str] = set()

    # Duyệt từng document huấn luyện để đếm token.
    for intent_name, text, _source in documents:
        # Token hóa nội dung document.
        tokens = _tokenize_with_hints(text)
        # Bỏ qua document không tạo ra token nào.
        if not tokens:
            continue

        # Tăng số document thuộc intent hiện tại.
        document_count_by_intent[intent_name] += 1
        # Cộng dồn số lần xuất hiện token cho intent hiện tại.
        token_counts_by_intent[intent_name].update(tokens)
        # Cập nhật từ vựng toàn cục.
        vocabulary.update(tokens)

    # Bổ sung token từ metadata của intent để mô hình vẫn có tín hiệu kể cả khi ít message/pattern.
    for intent in intents:
        hint_tokens = _intent_hint_tokens(intent)
        if hint_tokens:
            token_counts_by_intent[intent.name].update(hint_tokens)
            vocabulary.update(hint_tokens)

    # Tập tất cả intent gồm intent trong DB và intent xuất hiện trong document huấn luyện.
    all_intents = sorted(set(intent_names) | set(document_count_by_intent.keys()))
    # Tổng số document có nhãn dùng để tính prior probability.
    total_docs = sum(document_count_by_intent.values())
    # Hệ số smoothing Laplace để tránh xác suất bằng 0.
    smoothing = 1.0
    # Kích thước từ vựng tối thiểu là 1 để tránh chia cho 0.
    vocab_size = max(len(vocabulary), 1)

    # profiles chứa toàn bộ thống kê cần thiết cho từng intent.
    profiles: Dict[str, Dict[str, Any]] = {}
    for intent_name in all_intents:
        # Lấy bộ đếm token của intent, nếu chưa có thì dùng Counter rỗng.
        token_counts = token_counts_by_intent.get(intent_name, Counter())
        # Tổng số token của intent.
        token_total = sum(token_counts.values())
        # Số document huấn luyện thuộc intent này.
        doc_count = document_count_by_intent.get(intent_name, 0)
        # Tính log prior probability: log(P(intent)).
        # Dùng smoothing để intent ít dữ liệu vẫn có xác suất hợp lệ.
        prior_log_prob = math.log((doc_count + smoothing) / (total_docs + smoothing * max(len(all_intents), 1)))

        # Lưu thống kê của intent vào profile.
        profiles[intent_name] = {
            'doc_count': doc_count,
            'token_total': token_total,
            'prior_log_prob': prior_log_prob,
            'token_counts': dict(token_counts),
            # Lưu 30 token phổ biến nhất để debug và hỗ trợ evidence khi dự đoán.
            'top_tokens': [[token, count] for token, count in token_counts.most_common(30)],
        }

    # Snapshot là dữ liệu hoàn chỉnh của mô hình sau khi train.
    snapshot = {
        'model_name': MODEL_NAME,
        'version': f"{MODEL_NAME}-{_normalize_time_string()}",
        'trained_at': django_timezone.now().isoformat(),
        'document_count': total_docs,
        'intent_count': len(all_intents),
        'vocabulary_size': vocab_size,
        'profiles': profiles,
        'intent_names': all_intents,
    }

    # Lưu snapshot ra file JSON để lần sau không cần train lại.
    _save_snapshot_to_disk(snapshot)
    # Lưu metadata phiên bản mô hình vào database.
    _update_model_metadata(snapshot)
    # Trả về snapshot mới train.
    return snapshot


def get_intent_model_snapshot(force_refresh: bool = False) -> Dict[str, Any]:
    """Lấy snapshot mô hình hiện tại, hoặc train lại nếu chưa có/được yêu cầu refresh."""

    # Nếu force_refresh=True thì bỏ qua file cũ và train lại.
    snapshot = None if force_refresh else _load_snapshot_from_disk()
    # Nếu có snapshot hợp lệ trên disk thì dùng luôn.
    if snapshot:
        return snapshot
    # Nếu chưa có snapshot thì train mô hình mới.
    return train_intent_classifier(force=force_refresh)


def _scores_to_confidence(scores: Dict[str, float]) -> Tuple[Optional[str], float]:
    """Chuyển log-score của các intent thành intent tốt nhất và confidence tương đối."""

    # Nếu không có điểm nào thì không thể dự đoán intent.
    if not scores:
        return None, 0.0

    # Lấy intent có score cao nhất.
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    # Chuyển log-score sang dạng tương đối bằng trick trừ best_score để tránh overflow.
    exp_scores = {intent: math.exp(score - best_score) for intent, score in scores.items()}
    # Tổng điểm sau khi chuyển mũ, nếu rỗng thì dùng 1.0 để tránh chia cho 0.
    total = sum(exp_scores.values()) or 1.0
    # Confidence là tỷ lệ điểm của intent tốt nhất trên tổng điểm của tất cả intent.
    confidence = exp_scores[best_intent] / total

    # Làm tròn confidence 4 chữ số thập phân để dễ hiển thị/lưu trữ.
    return best_intent, round(float(confidence), 4)


def predict_intent(user_text: str, min_confidence: float = 0.35) -> IntentPrediction:
    """Dự đoán intent phù hợp nhất cho nội dung người dùng nhập vào."""

    # Lấy snapshot mô hình hiện tại; nếu chưa có thì hàm này sẽ tự train.
    snapshot = get_intent_model_snapshot()
    # Lấy profile thống kê của từng intent.
    profiles = snapshot.get('profiles', {})
    # Nếu chưa có profile thì trả về kết quả không dự đoán được.
    if not profiles:
        return IntentPrediction(None, 0.0, {}, [], snapshot.get('version'))

    # Token hóa câu người dùng nhập vào.
    input_tokens = _tokenize_with_hints(user_text)
    # Nếu câu nhập rỗng hoặc không có token hợp lệ thì không dự đoán.
    if not input_tokens:
        return IntentPrediction(None, 0.0, {}, [], snapshot.get('version'))

    # Đếm số lần xuất hiện của từng token trong câu nhập.
    token_counter = Counter(input_tokens)
    # Lấy kích thước từ vựng từ snapshot, tối thiểu là 1 để tránh chia cho 0.
    vocabulary_size = max(int(snapshot.get('vocabulary_size') or 0), 1)
    # Lưu log-score của từng intent.
    scores: Dict[str, float] = {}
    # Lưu các token bằng chứng theo từng intent.
    evidence_by_intent: Dict[str, List[str]] = {}
    # Tập token đầu vào để kiểm tra giao nhau nhanh hơn.
    input_token_set = set(input_tokens)

    # Tính điểm cho từng intent trong mô hình.
    for intent_name, profile in profiles.items():
        # Bộ đếm token đã học của intent hiện tại.
        token_counts = profile.get('token_counts', {})
        # Tổng token của intent, tối thiểu 1 để tránh chia cho 0.
        token_total = max(int(profile.get('token_total') or 0), 1)
        # Khởi tạo score bằng log prior probability của intent.
        score = float(profile.get('prior_log_prob') or 0.0)
        # Danh sách token đóng vai trò bằng chứng cho intent này.
        evidence: List[str] = []

        # Cộng log likelihood của từng token đầu vào theo công thức Naive Bayes.
        for token, count in token_counter.items():
            # Số lần token từng xuất hiện trong dữ liệu train của intent này.
            token_frequency = int(token_counts.get(token, 0) or 0)
            # Công thức Laplace smoothing: log((freq + 1) / (total_tokens + vocab_size)).
            score += count * math.log((token_frequency + 1.0) / (token_total + vocabulary_size))
            # Nếu token từng xuất hiện trong intent này thì đưa vào evidence.
            if token_frequency > 0:
                evidence.append(token)

        # Tạo token từ chính tên intent để tăng điểm nếu câu người dùng trùng với tên intent.
        intent_hint_tokens = set(tokenize_chat_text(intent_name.replace('_', ' ')))
        # Tìm phần giao nhau giữa token đầu vào và token tên intent.
        overlap = input_token_set.intersection(intent_hint_tokens)
        if overlap:
            # Cộng điểm thưởng khi người dùng nhập từ khóa trùng trực tiếp với tên intent.
            score += 0.6 + (0.1 * len(overlap))
            # Thêm token trùng vào evidence.
            evidence.extend(sorted(overlap))

        # Kiểm tra các token phổ biến nhất của intent có xuất hiện trong câu người dùng không.
        matched_top_tokens = [token for token, _count in profile.get('top_tokens', [])[:8] if token in input_token_set]
        if matched_top_tokens:
            # Cộng điểm nhẹ nếu câu người dùng chứa token top của intent.
            score += 0.15 * len(matched_top_tokens)
            # Thêm các top token khớp vào evidence.
            evidence.extend(matched_top_tokens)

        # Lưu score cuối cùng của intent.
        scores[intent_name] = score
        # Loại trùng evidence rồi sắp xếp cho dễ đọc.
        evidence_by_intent[intent_name] = sorted(set(evidence))

    # Chuyển bảng score thành intent tốt nhất và confidence.
    best_intent, confidence = _scores_to_confidence(scores)
    # Nếu không có intent tốt nhất hoặc confidence thấp hơn ngưỡng thì coi như không dự đoán được.
    if best_intent is None or confidence < min_confidence:
        return IntentPrediction(None, confidence, scores, [], snapshot.get('version'))

    # Trả về kết quả dự đoán đầy đủ.
    return IntentPrediction(
        intent_name=best_intent,
        confidence=confidence,
        scores=scores,
        evidence_tokens=evidence_by_intent.get(best_intent, []),
        model_version=snapshot.get('version'),
    )


def get_intent_model_status() -> Dict[str, Any]:
    """Trả về trạng thái hiện tại của mô hình intent classifier."""

    # Thử đọc snapshot từ disk.
    snapshot = _load_snapshot_from_disk()
    # Nếu chưa có snapshot thì ép train mới để tạo artifact.
    if not snapshot:
        snapshot = train_intent_classifier(force=True)

    # Trả về thông tin tổng quan để hiển thị trên admin/dashboard/API.
    return {
        'model_name': snapshot.get('model_name', MODEL_NAME),
        'version': snapshot.get('version'),
        'trained_at': snapshot.get('trained_at'),
        'document_count': snapshot.get('document_count', 0),
        'intent_count': snapshot.get('intent_count', 0),
        'vocabulary_size': snapshot.get('vocabulary_size', 0),
        'artifact_path': str(INTENT_MODEL_PATH),
        'available_intents': snapshot.get('intent_names', []),
        'has_artifact': INTENT_MODEL_PATH.exists(),
    }


def predict_top_intents(user_text: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Dự đoán và trả về danh sách các intent có điểm cao nhất."""

    # Gọi predict_intent với min_confidence=0.0 để luôn lấy score, kể cả khi confidence thấp.
    prediction = predict_intent(user_text, min_confidence=0.0)
    # Nếu không có bảng score thì trả về danh sách rỗng.
    if not prediction.scores:
        return []

    # Sắp xếp intent theo score giảm dần và lấy tối đa limit intent.
    ranked = sorted(prediction.scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    # Tính intent tốt nhất và confidence của intent đó.
    best_intent, best_confidence = _scores_to_confidence(prediction.scores)
    # Danh sách kết quả trả về cho frontend/API.
    results = []
    for intent_name, score in ranked:
        # Chỉ intent tốt nhất mới có confidence và evidence_tokens.
        # Các intent còn lại giữ confidence=0.0 để tránh hiểu nhầm là xác suất riêng lẻ.
        results.append({
            'intent_name': intent_name,
            'score': score,
            'confidence': best_confidence if intent_name == best_intent else 0.0,
            'evidence_tokens': prediction.evidence_tokens if intent_name == best_intent else [],
        })
    return results

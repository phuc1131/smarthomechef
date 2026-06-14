# Implementation Plan - Fix Chatbot AI Routing and Database Search False-Positives

This plan documents all files with AI-based chat and recipe-answering capabilities, identifies the root causes of the false-positive chatbot routing (such as "chào" matching "Cháo gà"), and proposes a list of detailed fixes.

## Files with AI Answering/Routing Capabilities

1. **[views.py](file:///c:/vscode/smart-home-chef(ai agent)/app/features/user_panel/views.py)**:
   - **Role**: Entrypoint for handling client-side chat requests (`chat_send`).
   - **Key Logic**: Performs intent classification, maps messages to predefined intents (like `recipe`, `recommendation`), falls back to database lookup (`_search_keyword_hardcoded`), and calls the AI orchestrator or local RAG.

2. **[ai_orchestrator_service.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/ai_orchestrator_service.py)**:
   - **Role**: Coordinates intent classification models, retrieves RAG evidence, evaluates policies, and decides between local DB routing or Gemini AI.

3. **[personalization_service.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/personalization_service.py)**:
   - **Role**: Computes Jaccard text similarities (`_text_similarity`), performs semantic search over foods, and ranks/scores food candidates based on user health profiles.

4. **[local_rag_service.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/local_rag_service.py)**:
   - **Role**: Synthesizes a local fallback response when offline or before fallback to Gemini, based on matched evidence (recipes, foods, ingredients).

5. **[intent_classifier.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/intent_classifier.py)**:
   - **Role**: Local keyword-based intent classifier.

6. **[semantic_intent_service.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/semantic_intent_service.py)**:
   - **Role**: TF-based local embedding intent classifier.

---

## Root Cause Analysis of Bug

When the user types general conversational inputs (such as "chào", "mày biết làm món gì", or "đang trả lời sai kìa"):
1. **No Intent Match**: The intent classifiers correctly fail to match specific action intents (like `recipe` or `shopping`), yielding `None`.
2. **Greedy Database Matching**: The view code runs `_search_keyword_hardcoded`. Because SQLite's text matching is accent-insensitive, "chào" matches "Chao ga". 
3. **No Similarity Threshold**: If there is no exact database match, `_search_keyword_hardcoded` falls back to `semantic_search_with_scores`, which uses `sim >= 0.0` and returns all database items. 
4. **Incorrect Personalization Boost**: Because "Chao ga" is `diabetes_friendly` or matches a stopword like "món" (in "mày biết làm món gì"), it gets high personalization scores, passes the minimal filters, and gets returned as an exact answer.
5. **RAG Interception**: The local RAG generator (`local_rag_service.py`) sees these dummy matched foods in the RAG context and hijacks the response instead of letting Gemini answer naturally.

---

## Proposed Changes

### Component: Chat Web View & Search Verification

#### [MODIFY] [views.py](file:///c:/vscode/smart-home-chef(ai agent)/app/features/user_panel/views.py)

We will modify:
1. **`chat_send`**:
   - Detect if the classified intent is conversational (`general`, `feedback`, `health_goal`, or `greeting`). If so, bypass the database search and route directly to the AI orchestrator.
2. **`_search_keyword_hardcoded`**:
   - Define a list of common Vietnamese and English greetings/conversational phrases (`GREETINGS_AND_CONVERSATION`). If the normalized query matches any, return `None` immediately.
   - Refine the similarity filter. Only return a matched food if the query has a high token overlap with the food's name:
     - The query is an exact match (case-insensitive or normalized).
     - Or all query tokens are a subset of the food's name tokens (e.g., query "cơm" matches "Cơm chiên").
     - Or the Jaccard similarity between query tokens and food name tokens is at least `0.30` (with both accent-sensitive and accent-insensitive checks).

### Component: Personalization & Semantic Search

#### [MODIFY] [personalization_service.py](file:///c:/vscode/smart-home-chef(ai agent)/app/services/personalization_service.py)

We will modify:
1. **`semantic_search_with_scores`**:
   - Change the similarity threshold from `sim >= 0.0` to `sim >= 0.25`. This prevents returning random database items when the user query is completely unrelated.
2. **`rank_food_candidates`**:
   - Only include the `query_sim` reason in `reasons` if `query_sim >= 0.25` to prevent displaying confusing low-similarity notes.

---

## Verification Plan

### Automated Tests
- Run tests: `.venv\Scripts\pytest` (when environment is resolved).

### Manual Verification
1. Open chat and type "chào" -> Should respond with greeting from AI, NOT "Chao ga".
2. Type "mày biết làm món gì" -> Should respond with AI capabilities, NOT "Chao ga".
3. Type "đang trả lời sai kìa" -> Should respond with AI apologies/correction, NOT "Bánh mì Sài Gòn".
4. Type "phở bò" -> Should instantly retrieve "Phở bò" from database.

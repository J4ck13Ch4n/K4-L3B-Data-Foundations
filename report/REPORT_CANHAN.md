# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Trần Hữu Đức
**MSSV**: 2A202602459
**Nhóm:** G63
**Ngày:** 20/09/2026

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity đo góc giữa hai vector embedding, không đo độ dài của chúng. Giá trị gần 1 nghĩa là hai vector gần như cùng hướng — với text embedding, điều đó nghĩa là hai đoạn văn bản có nội dung/ý nghĩa gần nhau, dù có thể dùng từ ngữ khác nhau. Giá trị gần -1 nghĩa là hai vector gần như đối lập hướng; giá trị gần 0 nghĩa là không liên quan (trực giao).

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua có thể gửi yêu cầu trả hàng trong 15 ngày."
- Câu B: "Khách hàng được phép yêu cầu hoàn tiền trong vòng mười lăm ngày."
- Tại sao tương đồng: khác từ vựng gần như hoàn toàn ("người mua" vs "khách hàng", "trả hàng" vs "hoàn tiền", "15 ngày" vs "mười lăm ngày") nhưng cùng diễn đạt một nội dung — một embedding hiểu ngữ nghĩa thật sự sẽ chấm hai câu này gần nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Người bán phải phản hồi trong 02 ngày lịch."
- Câu B: "Hôm nay trời mưa rất to ở Hà Nội."
- Tại sao khác: hai câu không liên quan về chủ đề (chính sách thương mại điện tử vs. thời tiết), không chia sẻ khái niệm nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Với text embedding, độ dài (magnitude) của vector thường phản ánh các yếu tố không liên quan đến ý nghĩa (như độ dài văn bản gốc), trong khi hướng của vector mới mang thông tin ngữ nghĩa. Cosine similarity bỏ qua độ dài và chỉ so sánh hướng, nên ổn định hơn Euclidean distance khi so sánh các văn bản có độ dài khác nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`.
> Đáp án: **23 chunks** — đã kiểm chứng lại bằng `FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)` trong `src/chunking.py` thật của tôi, ra đúng 23 phần tử.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với `overlap=100`: `ceil((10000-100)/(500-100)) = ceil(9900/400) = ceil(24.75) = 25` chunks — đã kiểm chứng lại bằng code, đúng 25. Tăng overlap làm bước nhảy (`step = chunk_size - overlap`) nhỏ lại nên số chunk **tăng** (23 → 25). Overlap lớn hơn tốn thêm chunk (và thêm chi phí embedding/lưu trữ) nhưng giảm rủi ro một câu/số liệu quan trọng bị cắt đúng vào ranh giới giữa hai chunk liên tiếp — với văn bản chính sách nhiều số liệu như corpus của tôi, mất một con số ở ranh giới chunk là lỗi retrieval nghiêm trọng.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?<=[.!?])\s+", text)` — lookbehind giữ dấu câu (`.`, `!`, `?`) gắn liền với câu nó kết thúc, tránh bẫy phổ biến là `re.split(r'[.!?]\s+', text)` sẽ nuốt mất dấu câu. Sau khi tách câu, gom từng nhóm `max_sentences_per_chunk` câu thành một chunk và `strip()` khoảng trắng thừa. Text rỗng trả về `[]` ngay từ đầu, không crash. Edge case tôi biết mình chưa xử lý: chữ viết tắt có dấu chấm (`TS.`, `v.v.`) hoặc số thập phân (`3.5 ngày`) sẽ bị nhận nhầm là ranh giới câu, làm câu bị cắt sai.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử lần lượt các separator theo độ ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Với mỗi separator: tách text thành các mảnh, gắn lại separator vào cuối mỗi mảnh (trừ mảnh cuối) để có thể ghép lại đúng nguyên văn bản gốc; mảnh nào vẫn dài hơn `chunk_size` thì đệ quy tiếp với danh sách separator còn lại (chiều "xuống sâu"); sau đó nối các mảnh liền kề đã đủ nhỏ lại với nhau tới sát `chunk_size` (chiều "gom lên") để tránh sinh ra hàng trăm mảnh vụn. Base case: nếu `remaining_separators` rỗng (kể cả khi gọi trực tiếp với `separators=[]`) hoặc gặp separator `""`, cắt cứng theo `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` không chunk gì cả — nhận list `Document` đã có sẵn (đã được chunk ở tầng ngoài, ví dụ trong `bench.py`) và append mỗi `Document` thành một record duy nhất qua `_make_record` (copy metadata, gán `doc_id` mặc định bằng `doc.id` nếu người gọi chưa có). Việc lưu trữ dùng list Python thuần (không dùng chromadb — đã xóa hẳn nhánh khởi tạo Chroma vì nó set `self._use_chroma = True` trước khi client thực sự được tạo, một bẫy khiến toàn bộ test store sập nếu máy tình cờ có cài chromadb). `search` gọi `_search_records` — hàm dùng chung tính điểm bằng dot product (`_dot`) giữa embedding câu hỏi và mọi record, sắp xếp giảm dần theo score, trả về top_k.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc **trước** khi tính similarity: xây danh sách `candidates` từ `self._store` chỉ giữ các record có mọi cặp `key: value` trong `metadata_filter` khớp, rồi mới gọi `_search_records` trên chính tập `candidates` đó — dùng lại đúng một đường code với `search()` để đảm bảo không lệch logic xếp hạng (test `test_no_filter_returns_all_candidates` kiểm tra chính xác điều này). Lọc trước quan trọng hơn lọc sau vì nếu xếp hạng top-k rồi mới loại bỏ record không khớp, có thể mất hết k slot cho tài liệu sai trong khi store vẫn còn tài liệu đúng đối tượng nằm sâu hơn. `delete_document` duyệt lại `self._store`, giữ mọi record có `metadata['doc_id']` khác giá trị cần xóa, trả về `True`/`False` tùy có phần tử nào thực sự bị loại hay không.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: (1) `store.search`/`search_with_filter` lấy top-k chunk; (2) nếu store rỗng, trả thẳng một câu thông báo cố định mà không gọi `llm_fn` (tránh gọi LLM vô ích trên ngữ cảnh trống); (3) nếu có kết quả, đánh số từng chunk `[1] [2] [3]` kèm `doc_id` làm nguồn, dựng prompt yêu cầu mô hình chỉ dùng đúng ngữ cảnh được cung cấp, trích dẫn số thứ tự khi trả lời, và nói rõ "không tìm thấy" nếu ngữ cảnh không chứa đáp án (ràng buộc chống bịa) — sau đó gọi `llm_fn(prompt)` và trả về kết quả.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: /mnt/d/AI_in_Action/day7/K4-L3B-Data-Foundations
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================== 42 passed in 0.30s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Chạy `compute_similarity(embedder(a), embedder(b))` thật trên **Gemini embedder** (`gemini-embedding-001`, qua `GeminiEmbedder`, cấu hình `EMBEDDING_PROVIDER=gemini` + `GEMINI_API_KEY` trong `.env`) cho 5 cặp câu lấy từ corpus và một câu đối lập chủ đề. Lần chạy đầu tiên dùng `MockEmbedder` cho kết quả hoàn toàn không đúng ý nghĩa (cặp diễn giải cùng nội dung ra điểm âm, cặp không liên quan ra điểm dương cao nhất) — sau khi đổi sang Gemini, cả 5 dự đoán đều đúng hướng.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế (Gemini) | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Người mua có thể gửi yêu cầu trả hàng trong 15 ngày." | "Khách hàng được phép yêu cầu hoàn tiền trong vòng mười lăm ngày." | cao | 0.8772 | **Đúng** |
| 2 | "Người bán phải phản hồi trong 02 ngày lịch." | "Hôm nay trời mưa rất to ở Hà Nội." | thấp | 0.5565 | **Đúng** (thấp hơn hẳn 3 cặp paraphrase: 0.88–0.98) |
| 3 | "Sản phẩm bị lỗi kỹ thuật do nhà sản xuất được bảo hành miễn phí." | "Sản phẩm hư hỏng do lỗi từ nhà sản xuất sẽ được bảo hành không tính phí." | cao | 0.9445 | **Đúng** |
| 4 | "Chính sách vận chuyển của Shopee áp dụng cho người bán." | "Con mèo của tôi rất thích ngủ trên ghế sofa." | thấp | 0.5152 | **Đúng** (thấp nhất trong 5 cặp) |
| 5 | "Thời hạn bảo hành qua Shopee là 20 đến 45 ngày làm việc." | "Thời gian bảo hành thông qua Shopee dao động từ 20 tới 45 ngày làm việc." | cao | 0.9804 | **Đúng** (cao nhất — gần như paraphrase 1:1) |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là mức "sàn" của điểm cosine: ngay cả 2 câu hoàn toàn không liên quan chủ đề (cặp 2, cặp 4) vẫn ra điểm dương khá cao (~0.51–0.56), chứ không gần 0 hay âm như trực giác "không liên quan = trực giao" gợi ý. Điều này cho thấy không gian embedding của Gemini có một "baseline" dương chung cho mọi câu tiếng Việt (có lẽ do đặc điểm ngôn ngữ/cấu trúc câu chung), nên **ngưỡng tuyệt đối không đáng tin — phải so sánh tương đối** giữa các ứng viên (điểm 0.55 "thấp" so với 0.88-0.98, nhưng vẫn cao hơn 0 rất nhiều). Đây cũng là lý do `search`/`search_with_filter` nên luôn xếp hạng (ranking) top-k thay vì đặt ngưỡng điểm cố định. So với lần chạy đầu bằng `MockEmbedder` (băm MD5, hoàn toàn ngẫu nhiên, cặp paraphrase 20-45 ngày ra điểm âm trong khi cặp "trời mưa" ra điểm dương cao nhất) thì Gemini phản ánh đúng ngữ nghĩa hơn rất nhiều, dù vẫn không đạt độ phân tách "sách giáo khoa" (gần 0 cho câu không liên quan).

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy 5 câu hỏi đánh giá của nhóm (xem `REPORT_NHOM.md` mục 3) trên `src/` cá nhân, áp dụng chiến lược **Chia nhỏ theo câu (`SentenceChunker`)** với `max_sentences_per_chunk=2` qua `bench.py`, với **Gemini embedder thật** (`gemini-embedding-001`, `EMBEDDING_PROVIDER=gemini` trong `.env`). Tổng số chunk sinh ra từ 7 tài liệu là **23 chunks**.

Lưu ý: đây là kết quả tầng **retrieval** (embedding) — tầng **sinh câu trả lời (LLM)** dùng `demo_llm` mặc định (echo lại đoạn đầu của prompt) vì chạy kiểm thử tự động, cột "Câu trả lời của Agent" phản ánh định dạng trích dẫn kèm `doc_id` của `KnowledgeBaseAgent`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Buyer return deadline *(filter: buyer)* | `buyer-return-eligibility-deadline` — "# Điều kiện và thời hạn... Người mua chỉ có thể yêu cầu trả hàng trong vòng 15 ngày..." | 0.8207 | **Có** — đúng tài liệu gold, top-1, đủ bằng chứng "15 ngày" (2/2 điểm) | `[DEMO LLM]` trích dẫn [1][2][3] với `doc_id=buyer-return-eligibility-deadline` |
| 2 | Seller obligation after return request *(filter: seller)* | `seller-refund-response-deadline` — "Người bán không phải chịu chi phí vận chuyển hoàn trả..." (chunk 2 có "02 ngày lịch") | 0.7865 | **Có** — đúng tài liệu gold, top-1, đủ bằng chứng "02 ngày lịch" trong ngữ cảnh (2/2 điểm) | `[DEMO LLM]` trích dẫn đúng `doc_id=seller-refund-response-deadline` |
| 3 | When buyer refund released *(filter: buyer)* | `buyer-refund-processing-review` — "Tiền hoàn chỉ được giải ngân cho người mua khi rơi vào một trong các trường hợp sau: người bán xác nhận đã nhận được sản phẩm hoàn trả..." | 0.7957 | **Có** — đúng tài liệu gold, top-1, đủ bằng chứng (2/2 điểm) | `[DEMO LLM]` trích dẫn đúng `doc_id=buyer-refund-processing-review` |
| 4 | Return reasons & evidence *(no filter)* | `buyer-return-eligibility-deadline` (gold `buyer-return-reasons-refund-timeline` lọt hạng 3, score 0.7660) | 0.7790 | **Liên quan** — gold nằm trong top-3, có bằng chứng "chưa mở hộp" (1/2 điểm) | `[DEMO LLM]` trích dẫn các tài liệu liên quan về điều kiện & lý do hoàn hàng |
| 5 | Who pays return shipping *(filter: seller)* | `seller-refund-response-deadline` — "Người bán không phải chịu chi phí vận chuyển... xác nhận đã nhận được Sản Phẩm Hoàn Trả..." | 0.8074 | **Có** — đúng tài liệu gold, top-1, đủ bằng chứng (2/2 điểm) | `[DEMO LLM]` trích dẫn đúng `doc_id=seller-refund-response-deadline` |

**Tổng điểm truy xuất đạt được:** **9/10** (4/5 câu đạt điểm tuyệt đối 2/2, 1/5 câu đạt 1/2 do tài liệu gold ở top-3).

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 câu (100%) đều chứa tài liệu gold và chuỗi bằng chứng trong top-3 kết quả trả về.

**Nhận xét về chiến lược SentenceChunker:**
- Với `max_sentences_per_chunk=2`, văn bản được cắt chính xác ở ranh giới câu mà không làm vỡ các điều khoản số liệu quan trọng (ví dụ "15 ngày", "02 ngày lịch").
- Số lượng chunk gọn gàng (23 chunks cho toàn bộ corpus 7 tài liệu), giúp tốc độ embedding nhanh và tiết kiệm chi phí gọi API.
- Đạt kết quả xuất sắc (9/10), ngang ngửa với chiến lược custom heading+paragraph và vượt trội so với Fixed-size (5/10) hay Recursive (5/10) khi cùng sử dụng Gemini embedder.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chiến lược `SentenceChunker` bảo toàn được tính hoàn chỉnh của ngữ pháp và ý nghĩa từng câu, đặc biệt hiệu quả với các tài liệu quy định/chính sách TMĐT chứa các mốc thời gian và điều kiện ràng buộc. Khi so sánh với các bạn trong nhóm dùng `FixedSizeChunker`, tôi nhận thấy việc cắt cứng theo ký tự dễ làm mất hoặc cắt đôi cụm từ khoá và số liệu quan trọng, khiến retrieval dù tìm đúng tài liệu nhưng context đưa cho LLM bị khuyết thông tin.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 9 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 *(42/42 test, có output thật)* |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 *(5/5 dự đoán đúng hướng với Gemini embedder thật)* |
| Kết quả truy xuất của tôi (Competition Results) | 9 / 10 *(5/5 câu có gold doc trong top-3, 4/5 đạt top-1)* |
| **Tổng phần cá nhân** | **58 / 60** |

> Điểm tự đánh giá trên là ước lượng dựa trên mức độ hoàn thành thực tế theo `docs/SCORING.md`, không thay thế đánh giá của giảng viên.

# Báo cáo nhóm G63 — Lab 7: Embedding & Vector Store

**Nhóm:** G63

**Thành viên:** Trần Hữu Đức; Doãn Hữu Nguyên; Lê Quang Ngọc; Nguyễn Thành Nam.

**Ngày cập nhật:** 20/09/2026

**Đề tài:** Truy xuất chính sách trả hàng và hoàn tiền trên Shopee.

Báo cáo tổng hợp từ bốn báo cáo cá nhân được bàn giao. Các kết quả được ghi theo điều kiện chạy và mức độ kiểm chứng; chưa có một lần chạy đồng bộ cả bốn chiến lược để xếp hạng công bằng. Tổng điểm tối đa phần nhóm là 40 theo [SCORING.md](../docs/SCORING.md), không phải điểm đã được chấm.

| Thành viên | Báo cáo nguồn | Chiến lược cá nhân |
|---|---|---|
| Trần Hữu Đức | [Báo cáo Đức](REPORT_CANHAN%20(tran%20huu%20duc).md) | SentenceChunker, 2 câu/chunk |
| Doãn Hữu Nguyên | [Báo cáo Nguyên](REPORT_CANHAN%20(Doan%20Huu%20Nguyen%20).md) | RecursiveChunker, chunk_size=500; báo cáo ghi overlap=50 |
| Lê Quang Ngọc | [Báo cáo Ngọc](REPORT_CANHAN.md) | Fixed-Size, 350 ký tự, overlap=35 |
| Nguyễn Thành Nam | [Báo cáo Nam](REPORT_CANHAN%20(nguyen%20thanh%20nam).md) | Semantic Similarity, threshold=0.35, max_chunk_size=420 |

## 1. Lựa chọn tài liệu — tối đa 10 điểm

### Chủ đề và lý do chọn

Chính sách trả hàng/hoàn tiền có nhu cầu tra cứu rõ ràng, nhiều mốc thời gian và điều kiện áp dụng khác nhau. Cùng một từ khóa “hoàn tiền” có thể chỉ thời hạn gửi yêu cầu, thời gian giải quyết hoặc thời gian tiền về; dữ liệu cũng phân biệt quyền và nghĩa vụ người mua/người bán. Đây là bối cảnh phù hợp để quan sát tác động của chunking và metadata filter tới việc lấy đúng bằng chứng.

Phạm vi gồm điều kiện và thời hạn trả hàng, bằng chứng, xử lý hoàn tiền, phí vận chuyển, trách nhiệm người bán; tài liệu bảo hành được giữ làm ngữ cảnh liên quan và ứng viên gây nhầm lẫn khi truy xuất.

### Danh mục corpus hiện được kiểm chứng trong workspace

Corpus `data/shopee-return-refund/` có **9 bản tóm lược từ 6 URL Shopee**, thu thập ngày 20/09/2026. Đây là phiên bản đang chạy trên máy Ngọc, được chuẩn bị để các thành viên đồng bộ, không khẳng định cả bốn đã dùng phiên bản này. Nguyên dùng đường dẫn `data/ecommerce/*.md`; Đức ghi 7 tài liệu với ID khác; Nam cũng chưa bàn giao manifest trùng phiên bản hiện tại.

| # | Tài liệu | Nguồn | Phiên bản | Ký tự thân bài | Audience / category |
|---|---|---|---|---:|---|
| 1 | [buyer-return-conditions](../data/shopee-return-refund/buyer-return-conditions.md) | [Shopee](https://help.shopee.vn/portal/4/article/77251) | effective-2026-03-11 | 986 | buyer / returns-policy |
| 2 | [seller-return-shipping](../data/shopee-return-refund/seller-return-shipping.md) | [Shopee](https://help.shopee.vn/portal/4/article/77251) | effective-2026-03-11 | 927 | seller / shipping-policy |
| 3 | [buyer-return-request](../data/shopee-return-refund/buyer-return-request.md) | [Shopee](https://help.shopee.vn/portal/4/article/79233) | not-stated | 634 | buyer / returns-policy |
| 4 | [buyer-refund-processing](../data/shopee-return-refund/buyer-refund-processing.md) | [Shopee](https://shopee.vn/blog/?p=188413) | published-2026-09-15 | 757 | buyer / refund-policy |
| 5 | [buyer-warranty-claim](../data/shopee-return-refund/buyer-warranty-claim.md) | [Shopee](https://help.shopee.vn/portal/4/article/77245) | updated-2025-01-03 | 418 | buyer / warranty-policy |
| 6 | [buyer-received-wrong-item](../data/shopee-return-refund/buyer-received-wrong-item.md) | [Shopee](https://help.shopee.vn/portal/4/article/79467) | not-stated | 694 | buyer / returns-policy |
| 7 | [seller-return-handling](../data/shopee-return-refund/seller-return-handling.md) | [Shopee](https://help.shopee.vn/portal/4/article/77251) | effective-2026-03-11 | 540 | seller / returns-policy |
| 8 | [seller-refund-dispute](../data/shopee-return-refund/seller-refund-dispute.md) | [Shopee](https://help.shopee.vn/portal/4/article/77265) | published-2024-03-15 | 516 | seller / refund-policy |
| 9 | [seller-warranty-obligations](../data/shopee-return-refund/seller-warranty-obligations.md) | [Shopee](https://help.shopee.vn/portal/4/article/77245) | updated-2025-01-03 | 370 | seller / warranty-policy |

Số ký tự tính trên thân bài đã bỏ frontmatter, trước chunking. Nhiều tài liệu chọn các mục khác nhau của cùng nguồn; 9 tài liệu không có nghĩa là 9 nguồn độc lập. Danh mục và hash: [sources.csv](../data/shopee-return-refund/sources.csv), [corpus audit](shopee_corpus_audit.json).

### Quản trị dữ liệu

- [x] Corpus hiện tại chỉ chứa thông tin chính sách công khai; không chứa hồ sơ khách hàng, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Có nhật ký robots.txt, HTTP, URL cuối và hash nguồn tại [shopee_crawl_log.json](shopee_crawl_log.json).
- [x] Mỗi MD có nguồn, ngày lấy, phiên bản, audience và category.
- [x] Loại điều hướng/vỏ trang; trang trợ giúp 79507 không có nội dung hữu ích bị loại, phần thời gian nhận tiền dùng bài blog Shopee đã crawl.
- [x] Ghi rõ `http-crawl-reviewed-summary`: bản tóm lược đối chiếu, không phải toàn văn chính sách.
- [ ] Đối chiếu hash corpus trên máy của cả bốn thành viên trước lần so sánh cuối.

`public-source` chỉ mô tả việc truy cập công khai, không phải giấy phép mở. `not-stated` nghĩa là trang không nêu phiên bản; không lấy ngày crawl làm ngày hiệu lực. HTML nguồn lưu tại `.cache/shopee/` trên máy thu thập, không nằm trong bộ tài liệu nộp mặc định. Phạm vi tóm lược có thể bỏ sót ngoại lệ ngoài câu hỏi benchmark.

| Metadata | Kiểu | Vai trò |
|---|---|---|
| doc_id | Chuỗi | Gắn các chunk về tài liệu gốc, phục vụ truy vết/xóa |
| audience | buyer / seller | Lọc đúng đối tượng trước khi xếp hạng |
| category | Chuỗi | Phân biệt trả hàng, hoàn tiền, vận chuyển, bảo hành |
| source_url, source_section | Chuỗi | Đối chiếu điều khoản tại nguồn |
| retrieved_at, document_version | Chuỗi | Phân biệt ngày lấy và phiên bản được công bố |
| language | vi | Xác định corpus tiếng Việt khi query có thể tiếng Anh |
| source_sha256 | Chuỗi | Kiểm tra bản nguồn; audit bổ sung hash từng MD |

## 2. Thiết kế chiến lược — tối đa 15 điểm

### Baseline trên cùng dữ liệu

Bảng sau lấy từ [shopee_baseline.json](shopee_baseline.json), do `ChunkingStrategyComparator.compare(chunk_size=350)` chạy trên ba tài liệu hiện tại của Ngọc. Fixed dùng overlap35, Sentence gom 3 câu, Recursive không overlap. Đây là baseline cục bộ, **khác** cấu hình Sentence 2 câu của Đức và Recursive500 của Nguyên.

| Tài liệu | Chiến lược | Số chunk | Ký tự TB | Nhận xét ranh giới |
|---|---|---:|---:|---|
| buyer-received-wrong-item | fixed_size | 3 | 254.67 | Có thể cắt giữa câu; overlap lặp nội dung |
| buyer-received-wrong-item | by_sentences | 4 | 172.00 | Giữ câu; không bảo đảm giới hạn 350 ký tự |
| buyer-received-wrong-item | recursive | 3 | 231.33 | Ưu tiên đoạn/dòng; có thể tách điều kiện khỏi kết luận |
| buyer-refund-processing | fixed_size | 3 | 275.67 | Có thể cắt giữa câu; overlap lặp nội dung |
| buyer-refund-processing | by_sentences | 3 | 251.33 | Giữ câu; không bảo đảm giới hạn 350 ký tự |
| buyer-refund-processing | recursive | 4 | 189.25 | Ưu tiên đoạn/dòng; có thể tách điều kiện khỏi kết luận |
| buyer-return-conditions | fixed_size | 4 | 272.75 | Có thể cắt giữa câu; overlap lặp nội dung |
| buyer-return-conditions | by_sentences | 4 | 245.00 | Giữ câu; không bảo đảm giới hạn 350 ký tự |
| buyer-return-conditions | recursive | 4 | 246.50 | Ưu tiên đoạn/dòng; có thể tách điều kiện khỏi kết luận |

Nam cũng báo cáo baseline ở kích thước 420: trên `buyer-return-request`, Semantic tạo 5 chunk (104.6 ký tự TB), trong khi Fixed/Sentence/Recursive đều tạo 2; trên `buyer-refund-processing` là 4 chunk (118.5); trên `seller-return-handling` là 3 chunk (168.3). Nam ghi rõ lần chạy dùng mock, nên các số này chỉ cho thấy cách pipeline phân mảnh ở lần chạy đó, chưa chứng minh khả năng chia theo ngữ nghĩa.

### Chiến lược của từng thành viên

**Trần Hữu Đức — Sentence-based.** Gom 2 câu/chunk, nhằm giữ trọn câu chứa mốc thời gian và điều kiện. Báo cáo ghi 23 chunk từ 7 tài liệu, embedding Gemini `gemini-embedding-001`. Ưu điểm là dễ kiểm tra nội dung; hạn chế là câu dài không bị chặn theo số ký tự và quan hệ giữa nhiều câu vẫn có thể bị tách. Agent dùng demo/echo, chưa đánh giá generation thật.

**Doãn Hữu Nguyên — Recursive.** Ưu tiên đoạn → dòng → câu → từ → ký tự, chia đoạn quá dài rồi gom các phần nhỏ. Báo cáo ghi chunk_size500, overlap50, 390 chunk từ `data/ecommerce/*.md`, dùng OpenAI `text-embedding-3-small`. Cần đối chiếu mã nguồn riêng để xác nhận overlap50: phần mô tả thuật toán trong báo cáo không giải thích bước overlap, còn Recursive ở workspace Ngọc không có tham số này. Giữ tham số như thông tin Nguyên báo cáo, không tự sửa thành cấu hình đã được kiểm chứng.

**Lê Quang Ngọc — Fixed-Size.** Cắt tối đa 350 ký tự/chunk, overlap35, bước dịch315; tổng 23 chunk từ 9 tài liệu. Model là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Chọn theo nguyên lý trong [chunking_experiment_report.md](../data/chunking_experiment_report.md); file tham khảo không ấn định tham số. Cách chia đơn giản và dễ dự đoán số chunk, nhưng có thể cắt ngang điều khoản; overlap chỉ hỗ trợ gần ranh giới, không nối được các mục ở xa nhau.

**Nguyễn Thành Nam — Semantic Similarity.** Tách câu, embedding từng câu, so cosine hai câu liền nhau; gom khi similarity ≥0.35 và độ dài không vượt420, ngược lại mở chunk mới. Báo cáo hiện chạy `mock fallback (not semantic)`, chưa phải thử nghiệm ngữ nghĩa thật. Có chi phí embedding câu và phụ thuộc ngưỡng/model; với thuật toán mô tả, **tăng threshold làm dễ tách hơn**, nên muốn giảm phân mảnh cần cân nhắc hạ ngưỡng hoặc đặt minimum chunk size. Đề xuất “tăng threshold để bớt ngắn” trong báo cáo Nam cần được sửa theo quan hệ này.

Mã giả theo mô tả của Nam, không phải xác nhận implementation đã bàn giao:

```text
for next_sentence in sentences:
    if similarity(previous_sentence, next_sentence) < threshold
       or length(current_chunk + next_sentence) > max_chunk_size:
        emit current_chunk
        start next chunk
    else:
        append next_sentence
```

### Tổng hợp kết quả thành viên, chưa xếp hạng

| Thành viên | Điều kiện chạy được báo cáo | Kết quả retrieval | Mức kiểm chứng / giới hạn |
|---|---|---|---|
| Đức | Sentence2; 7 tài liệu / 23 chunk; Gemini thật | Tự đánh giá 9/10; 5/5 có gold và chuỗi bằng chứng trong top-3 | Theo bảng báo cáo cá nhân; Q4 gold hạng3, Q2 cần đọc nhiều chunk; chưa có log đầy đủ cùng gold hiện tại |
| Nguyên | Recursive500, ghi overlap50; 390 chunk; OpenAI thật | Báo cáo 5/5 liên quan, Q3/Q5 một phần; chưa chốt điểm /10 | Corpus khác; Q5 không filter; Q2 nói riêng người bán Mall |
| Ngọc | Fixed350/35; 9 tài liệu / 23 chunk; MiniLM thật | 2/5 đủ toàn bộ chuỗi bằng chứng; proxy4/10 | Có JSON/log nội dung đầy đủ; proxy nghiêm ngặt không tương đương điểm Đức tự chấm |
| Nam | Semantic0.35/max420; mock fallback | Bảng ghi Q1/Q2/Q4/Q5 liên quan, Q3 một phần | Chưa có model thật; không dùng tự đánh giá10/10 để xếp hạng |

### Kết luận lựa chọn chiến lược chiến thắng tạm thời

**G63 chọn Sentence-based Chunking của Trần Hữu Đức, cấu hình 2 câu/chunk, làm phương án ưu tiên tạm thời cho đề tài chính sách trả hàng và hoàn tiền Shopee.** Theo báo cáo cá nhân Đức, chiến lược đạt mức tự đánh giá 9/10, cả 5 câu đều có tài liệu gold và chuỗi bằng chứng trong top-3; Q4 cần lấy gold ở hạng3. Cách chia giữ ranh giới câu, thuận tiện kiểm tra các mốc thời gian và điều kiện trong từng điều khoản. Đây là căn cứ để chọn phương án tiếp tục thử nghiệm và trình bày, chưa phải bằng chứng Sentence luôn tốt hơn ba chiến lược còn lại.

**Phạm vi của kết luận:** “chiến thắng tạm thời” là lựa chọn dựa trên các báo cáo đã bàn giao, không phải thứ hạng từ một thí nghiệm đồng bộ. Không so trực tiếp 9/10 của Đức với proxy4/10 của Ngọc, hoặc cosine Gemini với OpenAI/MiniLM: corpus, độ dài chunk, ngôn ngữ câu hỏi, filter và tiêu chí chấm khác nhau. Nhận xét Đức về Fixed/Recursive5/10 cùng Gemini là kết quả được Đức báo cáo, không gán các điểm đó cho Ngọc hoặc Nguyên. Agent của Đức vẫn dùng demo/echo, nên kết luận không bao gồm chất lượng sinh câu trả lời của LLM.

Trong đối chứng cùng môi trường hiện có trên máy Ngọc, **Fixed-Size350/overlap35 có proxy cao nhất: 4/10, so với Recursive350 và Heading350 cùng 3/10**; cả ba đều đủ bằng chứng cho 2/5 câu. Đối chứng này chưa có Sentence2 và Semantic thật, vì vậy không chứng minh hoặc bác bỏ lựa chọn tạm thời ở trên. Để xác nhận chiến thắng cuối cùng, nhóm cần chạy đủ bốn chiến lược trên cùng corpus/model/query/filter/gold và đối chiếu nội dung câu trả lời theo cùng rubric.

**Yêu cầu heading/section của biến thể L3B:** bốn chiến lược cá nhân hiện không có heading. Workspace Ngọc đã có một thí nghiệm bổ sung `HeadingChunker` trong [custom_chunking.py](../src/custom_chunking.py) và log trên cùng corpus/model/top-k. Cần trình bày thử nghiệm bổ sung này, đồng thời lưu ý nó chạy trên các mục của bản tóm lược, chưa kiểm tra toàn văn chính sách gốc nhiều tầng. Không đổi tên Semantic thành Heading để coi là đáp ứng.

## 3. Câu hỏi đánh giá và chất lượng truy xuất — tối đa 10 điểm

### Năm câu hỏi để đồng bộ lần so sánh cuối

Dùng nguyên văn câu hỏi tiếng Anh từ file Nam trong [benchmark_queries.json](../benchmark_queries.json). Gold dưới đây lấy từ corpus 9 tài liệu đang được kiểm chứng; không khẳng định các thành viên trước đó dùng cùng gold. Báo cáo Nguyên trình bày query tiếng Việt; Đức dùng nhãn rút gọn, chưa đủ để xác nhận chuỗi query thực tế trùng hoàn toàn.

| Câu | Query | Filter | Gold answer | Tài liệu bằng chứng |
|---|---|---|---|---|
| Q1 | How long does a buyer have to request a return or refund? | {'audience': 'buyer'} | 15 ngày từ khi đơn cập nhật giao thành công; thực phẩm tươi sống/đông lạnh 24 giờ. Quá hạn chỉ được xem xét hỗ trợ. | buyer-return-conditions |
| Q2 | What must a seller do after a buyer opens a return request? | {'audience': 'seller'} | Theo dõi thông báo Shopee, đối chiếu hàng hoàn. Khi không đồng ý quyết định hoặc hàng hoàn có vấn đề, phản hồi trong 2 ngày lịch từ thông báo, trừ thời hạn khác; không phản hồi được coi là đồng ý. | seller-return-handling, seller-return-shipping |
| Q3 | When is the buyer's refund released after a return is approved? | {'audience': 'buyer'} | Duyệt trả hàng chưa đồng nghĩa giải ngân ngay: tùy xác nhận nhận hàng, chấp thuận hoàn không trả hàng, hoặc quyết định hoàn sớm của Shopee. Tiền về tùy phương thức: thẻ 7–14 ngày làm việc, Napas 2–5 ngày làm việc, ví khoảng 24 giờ; COD/chuyển khoản về ngân hàng khoảng 2 ngày làm việc. Tính từ chấp nhận hoàn tiền, có thể phụ thuộc ngân hàng. | buyer-return-conditions, buyer-refund-processing |
| Q4 | Which reasons and evidence can support a return or refund claim? | Không | Các lý do: chưa nhận/thiếu hàng, giả/nhái, lỗi/hư, sai, khác mô tả, hết hạn, người bán đồng ý; không còn nhu cầu có điều kiện riêng. Bằng chứng tùy trường hợp: ảnh/video rõ tình trạng, mã vận đơn, số lượng, lịch sử trao đổi. Chưa nhận hàng không cần bằng chứng theo hướng dẫn Shopee. | buyer-return-conditions, buyer-received-wrong-item |
| Q5 | Who pays return shipping and what should the seller do with the parcel? | {'audience': 'seller'} | Phí phụ thuộc lỗi, loại yêu cầu và hình thức gửi: người bán chịu theo mục 7.1 nhưng có miễn trừ; người mua không trả phí lấy tại nhà/bưu cục, tự sắp xếp ứng phí rồi được hoàn/hỗ trợ theo điều kiện Mall/ngoài Mall. Người bán đối chiếu kiện và phản hồi vấn đề trong 2 ngày lịch từ thông báo, trừ thời hạn khác. | seller-return-shipping |

### Đối chiếu từng câu từ bốn báo cáo

“Đủ” ở cột Ngọc nghĩa là đủ toàn bộ chuỗi khai báo trong gold hiện tại; “liên quan” trong các báo cáo khác chưa chắc có cùng tiêu chuẩn. Mọi câu trả lời của agent được báo cáo hiện là demo/echo hoặc trích xuất, chưa có bằng chứng đánh giá LLM sinh thật.

| Câu | Đức — báo cáo cá nhân | Nguyên — báo cáo cá nhân | Ngọc — log hiện tại | Nam — báo cáo cá nhân |
|---|---|---|---|---|
| Q1 | Top-1 0.8207; có 15 ngày | Top-1 0.728; có 15 ngày và ngoại lệ24h | Đủ ở top-1; giữ ngoại lệ/quá hạn | `buyer-return-request#2`, ghi liên quan, mock |
| Q2 | Top-1 0.7865; cần thêm chunk chứa02 ngày | Top-1 0.630; nghĩa vụ người bán Mall, phạm vi hẹp | Chuỗi chính đủ top-1; đoạn sau bổ sung hậu quả | `seller-return-handling#1`, ghi liên quan, mock |
| Q3 | Top-1 0.7957; điều kiện giải ngân | Top-1 0.586 nhầm thời hạn yêu cầu; bảng hoàn tiền ở hạng3 | Thiếu thời gian theo phương thức và một số điều kiện | Top-1 sai tài liệu; hoàn tiền hạng3 theo mô tả |
| Q4 | Gold hạng3, score0.7660; tự chấm1/2 | Top-1 0.598; ghi liên quan điều kiện chung | Thiếu các chuỗi về lý do/bằng chứng; top-1 là bảo hành | Ghi liên quan, chưa có nội dung đầy đủ để chấm |
| Q5 | Top-1 0.8074; ghi đủ bằng chứng | Top-1 0.651; chỉ phần phí, không filter, thiếu nghĩa vụ seller | Có điều khoản phí, thiếu xử lý kiện/thời hạn | Ghi liên quan, mock; chưa có nội dung để chấm đủ hai vế |

### Thí nghiệm đối chứng cùng môi trường trên máy Ngọc

Kết quả từ [benchmark_results.json](benchmark_results.json), top-k3, cùng 9 tài liệu, model MiniLM và filter như bảng query:

| Chiến lược | Số chunk | Ký tự TB | Câu đủ bằng chứng @3 | Proxy /10 |
|---|---:|---:|---:|---:|
| fixed | 23 | 275.30 | 2/5 | 4 |
| recursive | 27 | 216.37 | 2/5 | 3 |
| heading | 27 | 233.07 | 2/5 | 3 |

Proxy: 2 nếu đủ chuỗi ngay top-1, 1 nếu cần top-2/3, 0 nếu chưa đủ. Proxy0 có thể vẫn có đáp án một phần, nên không thay rubric 2/1/0 cho chất lượng câu trả lời. Fixed có proxy cao hơn trong đối chứng này nhưng cả ba chỉ đủ2/5; chưa có Sentence2/Semantic thật trên cùng môi trường để so sánh bốn người.

### Metadata filter và lỗi truy xuất

Với Q2 trong đối chứng Recursive350 của Ngọc, bỏ filter làm top-3 thiếu “2 ngày lịch” và “thời hạn khác”; lọc seller đưa đoạn `seller-return-handling::02` trở lại hạng3. Fixed và Heading đã có đủ chuỗi Q2 trước lọc, nên không kết luận filter luôn tăng kết quả. Đây là log của baseline Ngọc, không phải kết quả Recursive500 của Nguyên.

Q5 của Nguyên không lọc và lấy nội dung phí phía người mua, thiếu nghĩa vụ người bán; đây là dấu hiệu cần kiểm tra filter nhưng chưa phải đối chứng có/không filter trên chính máy Nguyên. Cấu hình chung của Nam/Ngọc cho Q5 là seller. Q4 không filter ở cả hai lần chạy, nên không dùng Q4 để chứng minh hiệu quả lọc.

Ba lỗi được ghi nhận lặp lại:

1. **Nhầm mốc thời gian:** Q3 hỏi lúc nhận tiền nhưng lấy hạn gửi yêu cầu15 ngày. Nguyên, Nam và Ngọc đều ghi nhận lỗi cùng kiểu; số ngày đúng trong nguồn vẫn có thể trả lời sai câu hỏi.
2. **Thiếu một vế:** Q4 cần cả lý do lẫn bằng chứng; Q5 cần cả phí lẫn xử lý kiện. Top-3 chứa tài liệu gold không đảm bảo đủ tất cả điều kiện.
3. **Sai phạm vi:** chính sách buyer/seller và nghĩa vụ riêng Shopee Mall không thể dùng thay nhau. Filter audience hữu ích nhưng vẫn cần kiểm tra phạm vi cụ thể bên trong đoạn.

Hướng cải thiện: khóa corpus/gold/query trước khi thử; chia truy vấn nhiều vế thành truy vấn con; lấy thêm đoạn lân cận hoặc rerank, rồi đo lại với cùng cấu hình cho mọi chiến lược. Với Semantic, dùng embedding thật cho cả bước chia câu lẫn truy xuất và kiểm tra ngưỡng trên dữ liệu riêng, tránh điều chỉnh chỉ để nâng điểm năm câu hiện tại.

## 4. Thuyết trình và bài học nhóm — tối đa 5 điểm

### Kịch bản demo đã chuẩn bị

| Phần | Người trình bày đề xuất | Nội dung |
|---|---|---|
| Mở đầu và dữ liệu — 1 phút | Lê Quang Ngọc | Đề tài, nguồn, metadata, phiên bản corpus |
| Bốn chiến lược — 4 phút | Mỗi thành viên 1 phút | Thuật toán, tham số và một ranh giới chunk điển hình |
| Hai tình huống — 3 phút | Nguyên và Đức phối hợp | Q2 có/không filter; Q3 phân biệt hạn yêu cầu với nhận tiền |
| Giới hạn và cải tiến — 2 phút | Nguyễn Thành Nam | Mock và embedding thật; câu nhiều vế; điều kiện so sánh công bằng |

Demo có thể mở `bench.py` và [ket_qua_benchmark.txt](../ket_qua_benchmark.txt) để xem log Fixed/Recursive/Heading của Ngọc. Chưa có runner Semantic của Nam hoặc runner Sentence/Gemini của Đức trong workspace để trình diễn đúng kết quả riêng của họ. Bảng trên là kế hoạch trình bày, không phải biên bản demo đã diễn ra.

### Bài học từ báo cáo thành viên

Đức ghi nhận Sentence giữ trọn câu và mốc thời gian hơn cắt theo ký tự; đây là nhận xét cá nhân Đức đã viết, chưa được xem là kết luận đối chứng chung. Nguyên chỉ ra Q3 và Q5 có liên quan chủ đề nhưng lệch trọng tâm hoặc thiếu nghĩa vụ seller. Ngọc cho thấy kiểm tra đủ nội dung khắt khe hơn đếm doc_id. Nam ghi rõ mock không phản ánh ngữ nghĩa, do đó không thể dùng để chứng minh Semantic thắng.

Nếu làm lại, nhóm sẽ chốt manifest dữ liệu, query nguyên văn, filter, gold và model ngay trước khi chia việc. Mỗi thành viên lưu cả nội dung top-3, tham số chunker và câu trả lời agent, không chỉ score. Báo cáo tách chỉ số retrieval khỏi điểm generation và chỉ tổng hợp điểm chung sau khi thống nhất cùng quy tắc chấm.

## 5. Tự đánh giá và phần cần bổ sung trước khi nộp

| Tiêu chí | Điểm tối đa | Bằng chứng hiện có | Trạng thái |
|---|---:|---|---|
| Lựa chọn tài liệu | 10 | 9 MD, nguồn/metadata, crawl log, audit | Đủ kiểm kê cho corpus hiện tại; cần đồng bộ bốn máy |
| Thiết kế chiến lược | 15 | Đủ bốn mô tả cá nhân, baseline, đối chứng heading bổ sung | Cần xác minh implementation/overlap của Nguyên và artifact Nam |
| Chất lượng truy xuất | 10 | Đủ năm query/gold và tổng hợp lỗi bốn báo cáo | Chưa có kết quả đồng bộ để tự chấm điểm nhóm |
| Thuyết trình | 5 | Kịch bản và ví dụ demo đã chuẩn bị | Chưa có biên bản/đánh giá demo chung |
| **Tổng tối đa** | **40** | **Không cộng các điểm cá nhân khác tiêu chuẩn thành điểm nhóm** | **Chưa tự gán điểm cuối** |

- [ ] Các thành viên chạy cùng corpus/model/query/filter/gold; giữ chiến lược và tham số cá nhân được công bố để so sánh.
- [ ] Nam bàn giao `semantic_benchmark.py`, implementation Semantic và `SEMANTIC_SIMILARITY_RESULTS.md`; các file được báo cáo tham chiếu chưa có trong workspace hiện tại.
- [ ] Nguyên xác nhận overlap50, manifest và query/filter thực tế; đặc biệt Q5.
- [ ] Đức bàn giao nội dung top-3/gold và xác nhận query nguyên văn; không dùng riêng số9/10 để so với proxy Ngọc.
- [ ] Đính kèm thí nghiệm heading/section theo yêu cầu K4, nêu rõ phạm vi tóm lược và kiểm tra trên điều khoản gốc nếu được yêu cầu.
- [ ] Hoàn thành demo rồi bổ sung phản hồi thực tế; chấm điểm nhóm theo cùng rubric.

Bản tổng hợp này hoàn thiện phần nội dung từ các tài liệu đã bàn giao. Các mục chưa có dữ liệu được ghi rõ thay vì suy đoán kết quả hoặc trải nghiệm của thành viên.

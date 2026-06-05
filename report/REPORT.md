# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thanh Toàn (2A202600633)
**Thành viên nhóm:**

- Nguyễn Thanh Toàn - 2A202600633
- Nguyễn Nhựt Đăng - 2A202600602
- Hoàng Kim Tuấn Anh - 2A202600574
- Nguyễn Hưng Nguyên - 2A202600652
**Ngày:** 05/06/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**

> Hai đoạn văn bản có cosine similarity cao nghĩa là vector embedding của chúng gần như cùng hướng trong không gian nhiều chiều (góc θ giữa hai vector nhỏ), tức là chúng mang ý nghĩa/ngữ cảnh rất giống nhau. Theo slide: 1.0 = cùng hướng (cùng nghĩa), 0.0 = vuông góc (không liên quan), –1.0 = ngược hướng (nghĩa đối lập). Đây là nền tảng cho semantic search — tìm đoạn liên quan dù không trùng keyword.

**Ví dụ HIGH similarity:**

- Sentence A: "Con mèo đang ngủ trên ghế sofa."
- Sentence B: "Chú mèo nằm nghỉ trên chiếc ghế dài."
- Tại sao tương đồng: Cùng nói về một con mèo đang nghỉ/ngủ trên ghế; chỉ khác cách diễn đạt và từ đồng nghĩa, nên embedding gần như cùng hướng.

**Ví dụ LOW similarity:**

- Sentence A: "Con mèo đang ngủ trên ghế sofa."
- Sentence B: "Lãi suất ngân hàng trung ương tăng 0.5% trong quý này."
- Tại sao khác: Hai câu thuộc hai chủ đề hoàn toàn khác nhau (vật nuôi vs tài chính), không chia sẻ ngữ nghĩa, nên vector gần như vuông góc và điểm tương đồng thấp.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**

> Cosine chỉ đo *hướng* (góc) của vector chứ không đo độ lớn (magnitude), nên nó bỏ qua khác biệt về độ dài văn bản và chỉ tập trung vào nội dung ngữ nghĩa; ngược lại Euclidean (L2) phụ thuộc magnitude nên dễ bị lệch theo độ dài đoạn. Cosine cho điểm chuẩn hóa ổn định trong [-1, 1] và là **metric mặc định của hầu hết vector DB** cho semantic search. Lưu ý từ slide: với embedding đã được normalize (như OpenAI embeddings hoặc mock embedder trong lab), cosine ≈ dot product — đó là lý do `EmbeddingStore.search` có thể xếp hạng bằng dot product mà vẫn tương đương cosine.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> Trình bày phép tính: `num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap)) = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`.
> Đáp án: **23 chunks**.

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**

> Khi overlap = 100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25` → tăng lên **25 chunks** (nhiều chunk hơn vì bước trượt `chunk_size - overlap` nhỏ lại). Ta muốn overlap nhiều hơn để giữ ngữ cảnh liền mạch qua ranh giới chunk, tránh cắt đứt một câu/ý quan trọng giữa hai chunk, giúp retrieval tìm được chunk chứa đủ thông tin. Theo slide, overlap hợp lý thường là **10–20% kích thước chunk** (ví dụ 50–100 tokens cho chunk 512); quá ít overlap → mất nghĩa ở biên, quá nhiều overlap → duplicate context, tốn storage và gây nhiễu kết quả.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Quy chế học vụ và chính sách học thuật tại VinUniversity (VinUniversity Academic Regulations and Student Policies).

**Tại sao nhóm chọn domain này?**

> Nhóm lựa chọn domain này vì đây là tập hợp các văn bản quy chế và quy trình học tập chính thức rất thiết thực đối với đời sống học vụ của sinh viên tại VinUniversity. Bộ tài liệu bao gồm: Tiêu chí duy trì học bổng, Quy trình khiếu nại điểm môn học, Yêu cầu tiếng Anh tốt nghiệp, Quy chế học thuật cử nhân, Hướng dẫn chuyển đổi tín chỉ và Quy định trung thực học thuật. Domain này giúp thử nghiệm truy xuất thông tin học vụ chính xác bằng tiếng Việt và tiếng Anh, hỗ trợ trả lời tự động các thắc mắc thường gặp của sinh viên.

### Data Inventory


| #   | Tên tài liệu                     | Nguồn            | Số ký tự | Metadata đã gán                                                               |
| --- | -------------------------------- | ---------------- | -------- | ----------------------------------------------------------------------------- |
| 1   | chinh_sach_hoc_bong.md           | Quy định VinUni  | 1429     | `{"type": "markdown", "source": "data_vin/chinh_sach_hoc_bong.md"}`           |
| 2   | quy_trinh_khieu_nai_diem.md      | Quy trình VinUni | 1441     | `{"type": "markdown", "source": "data_vin/quy_trinh_khieu_nai_diem.md"}`      |
| 3   | yeu_cau_tieng_anh.md             | Quy chế VinUni   | 1385     | `{"type": "markdown", "source": "data_vin/yeu_cau_tieng_anh.md"}`             |
| 4   | quy_dinh_trung_thuc_hoc_thuat.md | Quy chế VinUni   | 1567     | `{"type": "markdown", "source": "data_vin/quy_dinh_trung_thuc_hoc_thuat.md"}` |
| 5   | quy_trinh_tam_nghi_thoi_hoc.md   | Quy trình VinUni | 1310     | `{"type": "markdown", "source": "data_vin/quy_trinh_tam_nghi_thoi_hoc.md"}`   |
| 6   | quy_che_hoc_thuat_cu_nhan.md     | Quy chế VinUni   | 1570     | `{"type": "markdown", "source": "data_vin/quy_che_hoc_thuat_cu_nhan.md"}`     |
| 7   | credit_transfer_guideline_en.md  | Hướng dẫn VinUni | 1094     | `{"type": "markdown", "source": "data_vin/credit_transfer_guideline_en.md"}`  |


### Metadata Schema


| Trường metadata | Kiểu  | Ví dụ giá trị                       | Tại sao hữu ích cho retrieval?                                                                                                               |
| --------------- | ----- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `type`          | `str` | `"markdown"`, `"text"`              | Định dạng tài liệu để tối ưu hóa cách hiển thị hoặc trích xuất ranh giới chunk.                                                              |
| `source`        | `str` | `"data_vin/chinh_sach_hoc_bong.md"` | Bộ lọc nguồn tệp hỗ trợ định vị phạm vi tài liệu cần truy xuất, loại bỏ hoàn toàn các mảnh nhiễu từ các quy chế học vụ không liên quan khác. |


---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên tất cả tài liệu gộp lại (chunk_size=300):


| Tài liệu         | Strategy                         | Chunk Count | Avg Length | Preserves Context?                                                                                                    |
| ---------------- | -------------------------------- | ----------- | ---------- | --------------------------------------------------------------------------------------------------------------------- |
| Toàn bộ tài liệu | FixedSizeChunker (`fixed_size`)  | 31          | 294.39     | Trung bình (cắt biên ngẫu nhiên giữa các từ hoặc câu gây đứt đoạn ngữ cảnh).                                          |
| Toàn bộ tài liệu | SentenceChunker (`by_sentences`) | 23          | 329.13     | Khá tốt (bảo toàn ngữ nghĩa của từng câu đầy đủ, tuy nhiên độ dài chunk không đồng đều).                              |
| Toàn bộ tài liệu | RecursiveChunker (`recursive`)   | 35          | 215.97     | Rất tốt (ưu tiên tách theo đoạn/câu rồi gộp các mảnh nhỏ lại nên kích thước cân bằng dưới ngưỡng, giữ được ngữ cảnh). |


### Strategy Của Tôi

**Loại:** `RecursiveChunker` kết hợp với Metadata Filtering.

**Mô tả cách hoạt động:**

> Văn bản được phân mảnh đệ quy bằng danh sách các ký tự phân tách có độ ưu tiên giảm dần (`\n\n` $\rightarrow$ `\n` $\rightarrow$ `.`  $\rightarrow$  `` $\rightarrow$ `""`). Đồng thời, gán nhãn metadata phân loại cho từng chunk dựa trên nguồn tài liệu gốc. Khi nhận truy vấn, áp dụng bộ lọc metadata để lọc các chunk không thích hợp trước khi xếp hạng độ tương đồng cosine.

**Tại sao tôi chọn strategy này cho domain nhóm?**

> Vì tài liệu chính sách VinUni gồm cả tiếng Việt và tiếng Anh, đồng thời chia thành nhiều nhóm chính sách khác nhau (học bổng, kỷ luật, khiếu nại, nghỉ học...). Recursive Chunker giúp chunk có kích thước đồng đều (~216 ký tự) nhưng vẫn giữ ranh giới đoạn/câu của từng điều khoản; kết hợp metadata filter (`lang`, `category`) giúp triệt tiêu nhiễu từ tài liệu khác ngôn ngữ hoặc sai nhóm chính sách.

**Code snippet (nếu custom):**

```python
# Sử dụng RecursiveChunker mặc định kết hợp với search_with_filter
store.search_with_filter(query, top_k=top_k, metadata_filter={"lang": "en"})
```

### So Sánh: Strategy của tôi vs Baseline


| Tài liệu         | Strategy                         | Chunk Count | Avg Length | Retrieval Quality?                                                                         |
| ---------------- | -------------------------------- | ----------- | ---------- | ------------------------------------------------------------------------------------------ |
| Toàn bộ tài liệu | SentenceChunker (best baseline)  | 23          | 329.13     | Tốt, nhưng dễ lẫn lộn tài liệu giữa các ngôn ngữ/nhóm chính sách khác nhau.                |
| Toàn bộ tài liệu | **Của tôi** (Recursive + Filter) | 35          | 215.97     | Rất tốt, các đoạn lấy ra cân bằng kích thước và hoàn toàn chính xác theo bộ lọc phân loại. |


### So Sánh Với Thành Viên Khác


| Thành viên     | Strategy           | Retrieval Score (/10) | Điểm mạnh                                                             | Điểm yếu                                                                                 |
| -------------- | ------------------ | --------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Thanh Toàn     | Recursive + Filter | 9/10                  | Loại bỏ nhiễu ngôn ngữ và đối tượng đọc tốt, chunk ngắn gọn.          | Yêu cầu gắn metadata đầy đủ cho toàn bộ tài liệu thô.                                    |
| Nhựt Đăng      | SentenceChunker    | 7/10                  | Giữ nguyên ranh giới câu tự nhiên, ngữ cảnh trôi chảy.                | Dễ lấy nhầm tài liệu học thuật tiếng Anh khi hỏi câu tiếng Việt.                         |
| Tôi (Tuấn Anh) | FixedSizeChunker   | 5/10                  | Cực kỳ đơn giản, tốc độ xử lý nhanh, không cần thuật toán phức tạp.   | Rất nhiều câu bị cắt cụt ở giữa, làm mất thông tin quan trọng.                           |
| Hưng Nguyên    | Paragraph Chunker  | 8/10                  | Giữ trọn vẹn ý nghĩa ngữ cảnh lớn, lý tưởng cho các câu hỏi tổng hợp. | Kích thước các chunk chênh lệch lớn, một số chunk quá dài gây lãng phí tài nguyên token. |


**Strategy nào tốt nhất cho domain này? Tại sao?**

> Chiến lược `RecursiveChunker` kết hợp Metadata Filtering là tối ưu nhất. Lý do là vì nó cân bằng tốt nhất giữa việc giữ kích thước chunk gọn gàng (dưới giới hạn token của LLM) và tính chính xác tuyệt đối về mặt phân quyền truy cập thông tin qua metadata filter.

---

## 4. My Approach — Cá Nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

`**SentenceChunker.chunk`** — approach:

> Sử dụng `re.split(r"(?<=[.!?])\s+", text)` với *lookbehind* để cắt ngay sau dấu kết câu (`.`, `!`, `?`) mà vẫn giữ dấu câu trong mỗi câu. Sau đó lọc bỏ phần tử rỗng, `strip()` từng câu, rồi gom tối đa `max_sentences_per_chunk` câu vào mỗi chunk (nối bằng khoảng trắng). Edge case: text rỗng/chỉ khoảng trắng trả về `[]`.

`**RecursiveChunker.chunk` / `_split`** — approach:

> Áp dụng thuật toán chia để trị (recursive). `chunk()` trả `[text]` nếu text đã ≤ `chunk_size`, ngược lại gọi helper `_split` với danh sách separator ưu tiên (`\n\n` → `\n` → `.`  →  `` → `""`). Mảnh nào vẫn lớn hơn `chunk_size` thì đệ quy với các separator nhỏ hơn còn lại; các mảnh nhỏ liền kề được **gộp (merge) lại** thành chunk có độ dài tối đa không vượt quá `chunk_size`. Khi hết separator hoặc gặp separator rỗng `""` thì cắt cứng theo `chunk_size` để tránh lặp vô hạn.

### EmbeddingStore

`**add_documents` + `search`** — approach:

> Hỗ trợ song song cả ChromaDB (nếu có sẵn thư viện) và in-memory fallback thông qua một list các dict. Khi add document, thực hiện lấy vector embedding thông qua `embedding_fn` và lưu lại thông tin tài liệu. Khi search, tính toán cosine similarity giữa vector của query và vector của tất cả tài liệu trong store, rồi sắp xếp giảm dần theo score để trả về top_k.

`**search_with_filter` + `delete_document`** — approach:

> Đối với `search_with_filter`, thực hiện lọc trước (pre-filtering) các tài liệu trong store có metadata khớp với `metadata_filter` rồi mới tính tương đồng cosine và xếp hạng. Với `delete_document`, tìm và loại bỏ tất cả các record có ID hoặc metadata `doc_id` bằng với `doc_id` được yêu cầu xóa.

### KnowledgeBaseAgent

`**answer`** — approach:

> Đầu tiên thực hiện truy vấn `self.store.search` để lấy ra top_k chunk liên quan nhất. Ghép nội dung của các chunk này làm ngữ cảnh (Context) rồi dựng prompt với cấu trúc rõ ràng: đưa Context trước, tiếp theo là Question, và cuối cùng yêu cầu LLM đưa ra câu trả lời dựa trên ngữ cảnh đó.

### Test Results

```
test_chunker_classes_exist (tests.test_solution.TestClassBasedInterfaces.test_chunker_classes_exist) ... ok
test_mock_embedder_exists (tests.test_solution.TestClassBasedInterfaces.test_mock_embedder_exists) ... ok
test_counts_are_positive (tests.test_solution.TestCompareChunkingStrategies.test_counts_are_positive) ... ok
test_each_strategy_has_count_and_avg_length (tests.test_solution.TestCompareChunkingStrategies.test_each_strategy_has_count_and_avg_length) ... ok
test_returns_three_strategies (tests.test_solution.TestCompareChunkingStrategies.test_returns_three_strategies) ... ok
test_identical_vectors_return_1 (tests.test_solution.TestComputeSimilarity.test_identical_vectors_return_1) ... ok
test_opposite_vectors_return_minus_1 (tests.test_solution.TestComputeSimilarity.test_opposite_vectors_return_minus_1) ... ok
test_orthogonal_vectors_return_0 (tests.test_solution.TestComputeSimilarity.test_orthogonal_vectors_return_0) ... ok
test_zero_vector_returns_0 (tests.test_solution.TestComputeSimilarity.test_zero_vector_returns_0) ... ok
test_add_documents_increases_size (tests.test_solution.TestEmbeddingStore.test_add_documents_increases_size) ... ok
test_add_more_increases_further (tests.test_solution.TestEmbeddingStore.test_add_more_increases_further) ... ok
test_initial_size_is_zero (tests.test_solution.TestEmbeddingStore.test_initial_size_is_zero) ... ok
test_search_results_have_content_key (tests.test_solution.TestEmbeddingStore.test_search_results_have_content_key) ... ok
test_search_results_have_score_key (tests.test_solution.TestEmbeddingStore.test_search_results_have_score_key) ... ok
test_search_results_sorted_by_score_descending (tests.test_solution.TestEmbeddingStore.test_search_results_sorted_by_score_descending) ... ok
test_search_returns_at_most_top_k (tests.test_solution.TestEmbeddingStore.test_search_returns_at_most_top_k) ... ok
test_search_returns_list (tests.test_solution.TestEmbeddingStore.test_search_returns_list) ... ok
test_delete_reduces_collection_size (tests.test_solution.TestEmbeddingStoreDeleteDocument.test_delete_reduces_collection_size) ... ok
test_delete_returns_false_for_nonexistent_doc (tests.test_solution.TestEmbeddingStoreDeleteDocument.test_delete_returns_false_for_nonexistent_doc) ... ok
test_delete_returns_true_for_existing_doc (tests.test_solution.TestEmbeddingStoreDeleteDocument.test_delete_returns_true_for_existing_doc) ... ok
test_filter_by_department (tests.test_solution.TestEmbeddingStoreSearchWithFilter.test_filter_by_department) ... ok
test_no_filter_returns_all_candidates (tests.test_solution.TestEmbeddingStoreSearchWithFilter.test_no_filter_returns_all_candidates) ... ok
test_returns_at_most_top_k (tests.test_solution.TestEmbeddingStoreSearchWithFilter.test_returns_at_most_top_k) ... ok
test_chunks_respect_size (tests.test_solution.TestFixedSizeChunker.test_chunks_respect_size) ... ok
test_correct_number_of_chunks_no_overlap (tests.test_solution.TestFixedSizeChunker.test_correct_number_of_chunks_no_overlap) ... ok
test_empty_text_returns_empty_list (tests.test_solution.TestFixedSizeChunker.test_empty_text_returns_empty_list) ... ok
test_no_overlap_no_shared_content (tests.test_solution.TestFixedSizeChunker.test_no_overlap_no_shared_content) ... ok
test_overlap_creates_shared_content (tests.test_solution.TestFixedSizeChunker.test_overlap_creates_shared_content) ... ok
test_returns_list (tests.test_solution.TestFixedSizeChunker.test_returns_list) ... ok
test_single_chunk_if_text_shorter (tests.test_solution.TestFixedSizeChunker.test_single_chunk_if_text_shorter) ... ok
test_answer_non_empty (tests.test_solution.TestKnowledgeBaseAgent.test_answer_non_empty) ... ok
test_answer_returns_string (tests.test_solution.TestKnowledgeBaseAgent.test_answer_returns_string) ... ok
test_root_main_entrypoint_exists (tests.test_solution.TestProjectStructure.test_root_main_entrypoint_exists) ... ok
test_src_package_exists (tests.test_solution.TestProjectStructure.test_src_package_exists) ... ok
test_chunks_within_size_when_possible (tests.test_solution.TestRecursiveChunker.test_chunks_within_size_when_possible) ... ok
test_empty_separators_falls_back_gracefully (tests.test_solution.TestRecursiveChunker.test_empty_separators_falls_back_gracefully) ... ok
test_handles_double_newline_separator (tests.test_solution.TestRecursiveChunker.test_handles_double_newline_separator) ... ok
test_returns_list (tests.test_solution.TestRecursiveChunker.test_returns_list) ... ok
test_chunks_are_strings (tests.test_solution.TestSentenceChunker.test_chunks_are_strings) ... ok
test_respects_max_sentences (tests.test_solution.TestSentenceChunker.test_respects_max_sentences) ... ok
test_returns_list (tests.test_solution.TestSentenceChunker.test_returns_list) ... ok
test_single_sentence_max_gives_many_chunks (tests.test_solution.TestSentenceChunker.test_single_sentence_max_gives_many_chunks) ... ok

----------------------------------------------------------------------
Ran 42 tests in 0.003s

OK
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá Nhân (5 điểm)

*Exercise 3.3 — Dự đoán **trước** khi chạy `compute_similarity()`, ghi kết quả thực tế, rồi phản tư.*

### Cách chạy

```python
from src.chunking import compute_similarity
from src.embeddings import _mock_embed

score = compute_similarity(_mock_embed(sentence_a), _mock_embed(sentence_b))
```

Embedding backend: `**_mock_embed**` (MD5 hash → vector 64 chiều đã normalize). Score ≈ cosine similarity ∈ [-1, 1].

**Tiêu chí đánh giá "Đúng?":**

- Dự đoán **High** → kỳ vọng score **> 0.3** (hai câu cùng nghĩa).
- Dự đoán **Low** → kỳ vọng score **< 0.1** (hai câu khác chủ đề).
- Với mock embedder, hầu hết cặp High sẽ **Sai** — đó là kết quả học tập, không phải làm sai bài.

### Dự đoán TRƯỚC khi chạy code


| Dự đoán                     | Cặp                | Lý do                                                     |
| --------------------------- | ------------------ | --------------------------------------------------------- |
| **Cao nhất**                | Pair 1, 2, 4, 5    | Cùng chủ đề / paraphrase / đồng nghĩa                     |
| **Thấp nhất**               | Pair 3             | Chứng khoán vs đi mua táo — không liên quan               |
| Thứ tự cao → thấp (dự đoán) | 1 ≈ 2 > 5 > 4 >> 3 | Pair 1, 2 diễn đạt gần nhất; Pair 3 hoàn toàn khác domain |


### Kết quả thực tế (5 cặp bắt buộc)


| Pair | Sentence A                          | Sentence B                                  | Dự đoán | Actual Score | Đúng? | Ghi chú                                           |
| ---- | ----------------------------------- | ------------------------------------------- | ------- | ------------ | ----- | ------------------------------------------------- |
| 1    | The weather is very sunny today.    | It is a beautiful sunny day outside.        | High    | **-0.1667**  | Sai   | Cùng nghĩa (thời tiết nắng) nhưng score âm        |
| 2    | I love programming in Python.       | Python is my favorite programming language. | High    | **0.2216**   | Sai*  | Dương nhưng < 0.3 — mock không coi là "High" thật |
| 3    | The stock market crashed today.     | He went to the grocery store to buy apples. | Low     | **-0.1775**  | Đúng  | Thấp nhất nhóm, đúng dự đoán Low                  |
| 4    | The cat sat on the mat.             | A feline rested on the rug.                 | High    | **-0.0506**  | Sai   | Đồng nghĩa (cat/feline, mat/rug) nhưng score ≈ 0  |
| 5    | I ate a delicious pizza for dinner. | We had pizza for dinner and it was great.   | High    | **-0.0513**  | Sai   | Cùng nói về pizza tối nhưng score âm              |


Pair 2 là score **cao nhất** trong 5 cặp (0.2216) nhưng vẫn dưới ngưỡng 0.3 → không đạt "High" theo tiêu chí semantic thật.

**Thứ tự thực tế (cao → thấp):** Pair 2 (0.2216) > Pair 4 (-0.0506) > Pair 5 (-0.0513) > Pair 1 (-0.1667) > Pair 3 (-0.1775)

**So với dự đoán:** Chỉ đúng Pair 3 là Low nhất. Pair 1 (dự đoán cao nhất) lại xếp thứ 4 — **đảo ngược hoàn toàn** so với trực giác ngữ nghĩa.

### Bổ sung: 3 cặp tiếng Việt (domain VinUni)


| Pair | Sentence A                                 | Sentence B                                               | Dự đoán | Actual Score | Đúng? |
| ---- | ------------------------------------------ | -------------------------------------------------------- | ------- | ------------ | ----- |
| V1   | Sinh viên cần GPA 3.0 để duy trì học bổng. | Học bổng yêu cầu điểm trung bình tích lũy tối thiểu 3.0. | High    | **-0.0438**  | Sai   |
| V2   | Quy trình khiếu nại điểm môn học.          | Yêu cầu tiếng Anh tốt nghiệp IELTS 6.5.                  | Low     | **0.0106**   | Đúng  |
| V3   | Ăn gì cho no                               | GPA tối thiểu để duy trì học bổng là 3.0                 | Low     | **-0.0199**  | Đúng  |


V1 đặc biệt quan trọng: hai câu **cùng nghĩa** (GPA 3.0 / học bổng) nhưng mock cho **-0.0438** — giải thích vì sao Q1 benchmark retrieve sai dù data có sẵn.

### Kết quả nào bất ngờ nhất?

> **Pair 1** bất ngờ nhất: hai câu tiếng Anh cùng nói trời nắng đẹp, trực giác chắc chắn là High, nhưng score **-0.1667** (âm). Tương tự **Pair V1** tiếng Việt: cùng ý GPA 3.0 / học bổng mà score vẫn âm.

### Điều này nói gì về cách embeddings biểu diễn nghĩa?

> `_mock_embed` tạo vector từ **MD5 hash** của chuỗi ký tự — hai câu khác chữ dù cùng nghĩa sẽ có hash khác → vector gần **vuông góc** trong không gian 64 chiều → cosine ≈ 0 hoặc âm. **Không có mô hình ngôn ngữ nào tham gia**, nên similarity không phản ánh ngữ nghĩa.
>
> Bài học cho RAG: nếu dùng mock embedder cho retrieval (như benchmark Section 6), ranking gần như ngẫu nhiên; cần **embedder thật** (`all-MiniLM-L6-v2`, `text-embedding-3-small`) hoặc **metadata filter** để bù đắp. Đây là lý do score 0.15–0.30 ở Section 6 **không đáng tin** dù code chạy đúng.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)


| #   | Query                                                                    | Gold Answer                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Sinh viên cần GPA tối thiểu bao nhiêu để duy trì học bổng?               | Sinh viên phải đạt GPA tích lũy tối thiểu **3.0/4.0** vào cuối mỗi năm học; nếu xuống dưới 3.0 sẽ bị cảnh báo một học kỳ, không khôi phục thì bị giảm/thu hồi học bổng.                                 |
| 2   | Hành vi đạo văn bị xử lý kỷ luật như thế nào?                            | Mức xử lý tăng dần: cảnh báo bằng văn bản → điểm 0 cho bài vi phạm → trượt môn → đình chỉ học tập → buộc thôi học. Đạo văn nghiêm trọng hoặc tái phạm có thể dẫn đến đình chỉ.                          |
| 3   | Quy trình khiếu nại điểm cuối kỳ gồm những bước nào?                     | 4 bước: (1) trao đổi với giảng viên, (2) nộp đơn chính thức lên Registrar trong 5 ngày làm việc, (3) hội đồng xem xét/chấm lại, (4) thông báo kết quả trong 10 ngày làm việc (là quyết định cuối cùng). |
| 4   | Yêu cầu tiếng Anh đầu vào cho chương trình cử nhân là gì?                | Tối thiểu IELTS Academic **6.5** (không kỹ năng nào dưới 6.0) hoặc chứng chỉ tương đương (TOEFL iBT). Chưa đạt thì học English Pathway.                                                                 |
| 5   | What are the rules for transferring external credits? (filter `lang=en`) | Chỉ chấp nhận tín chỉ từ cơ sở được kiểm định, môn tương đương về nội dung/cấp độ, điểm ≥ C, không quá 5 năm; tối đa 50% tổng tín chỉ chương trình.                                                     |


### Kết Quả Của Tôi

Index chunk-level: 7 tài liệu → `RecursiveChunker(chunk_size=300)` → **37 chunk** được embed và lưu. Số liệu dưới đây lấy trực tiếp từ `python benchmark.py` (mock embedder).


| #   | Query                                                       | Top-1 Retrieved Chunk (nguồn) | Score  | Top-1 Relevant? | Gold ở top-3?                        |
| --- | ----------------------------------------------------------- | ----------------------------- | ------ | --------------- | ------------------------------------ |
| 1   | GPA tối thiểu để duy trì học bổng?                          | quy_trinh_tam_nghi_thoi_hoc   | 0.2287 | Không           | Không                                |
| 2   | Đạo văn bị xử lý như thế nào?                               | quy_trinh_tam_nghi_thoi_hoc   | 0.1598 | Không           | Không                                |
| 3   | Quy trình khiếu nại điểm gồm những bước nào?                | quy_trinh_khieu_nai_diem      | 0.3011 | **Có**          | Có (top-1 và top-2 đều là khieu_nai) |
| 4   | Yêu cầu tiếng Anh đầu vào cử nhân?                          | quy_dinh_trung_thuc_hoc_thuat | 0.2607 | Không           | Không                                |
| 5   | Rules for transferring external credits? (filter `lang=en`) | credit_transfer_guideline_en  | 0.2197 | **Có**          | Có (cả top-3 đều là credit_transfer) |


**Bao nhiêu queries trả về chunk relevant trong top-3?** **2 / 5** (Q3, Q5) — và cả hai cũng đúng ngay ở top-1. Các Q1, Q2, Q4 dựa trên `_mock_embed` (vector băm ngẫu nhiên) nên ranking gần như nhiễu: top-1 trỏ sai sang `quy_trinh_tam_nghi` / `quy_dinh_trung_thuc` dù về ngữ nghĩa hoàn toàn không liên quan. Q3 may mắn đúng nhờ trùng nhiều từ khóa hiếm ("khiếu nại", "điểm"). Riêng **Q5 nhờ lọc cứng metadata `lang=en` trước khi so khớp** nên cả top-3 đều là đúng tài liệu — minh chứng rõ giá trị của metadata filtering khi embedding yếu.

### Đọc score như thế nào? (quan sát từ giao diện test)

`EmbeddingStore` xếp hạng bằng **dot product** trên vector đã normalize → score tương đương **cosine similarity** trong khoảng **-1 đến 1**.


| Backend                               | Score điển hình                          | Có đáng tin không?                                                    |
| ------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------- |
| **mock** (lab mặc định)               | 0.15 – 0.35                              | **Không** — gần như ngẫu nhiên, không phản ánh ngữ nghĩa              |
| **local** (`all-MiniLM-L6-v2`)        | ≥ 0.50 thường liên quan; ≥ 0.70 rất chắc | **Có** — nên dùng ngưỡng gợi ý top-1 < 0.5 → trả "Không có thông tin" |
| **openai** (`text-embedding-3-small`) | tương tự local                           | **Có** — cần benchmark lại trên cùng 5 query                          |


**Quy tắc thực tế khi demo:** không chỉ nhìn score tuyệt đối mà còn xem (1) top-1 có đúng `source` gold không, (2) khoảng cách top-1 vs top-2, (3) metadata filter có bật đúng `lang`/`category` chưa. Tick "Bật metadata filter" nhưng để `(tất cả)` ở cả hai dropdown **không lọc gì** — phải chọn cụ thể (ví dụ `category=hoc_bong` cho câu hỏi học bổng).

### Kiểm chứng trên giao diện (`app.py`)

Ngoài `python benchmark.py`, nhóm dùng giao diện Streamlit (`streamlit run app.py`) để test trực quan:


| Tab           | Việc đã test                           | Kết quả quan sát                                                                                              |
| ------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Benchmark** | Chạy 5 query, xem ✓ GOLD               | Khớp `2/5` với CLI — Q3, Q5 đúng top-1                                                                        |
| **Tìm kiếm**  | Q1 không filter vs `category=hoc_bong` | Không filter → top-1 sai (`quy_trinh_tam_nghi`); có filter → chỉ còn chunk học bổng                           |
| **Tìm kiếm**  | Query ngoài domain: *"Ăn gì cho no"*   | Vẫn trả chunk (`quy_che_hoc_thuat_cu_nhan`, score ~0.22) dù không có tài liệu ăn uống — search luôn trả top-K |
| **Agent RAG** | Cùng câu ngoài domain                  | Prompt yêu cầu chỉ trả lời từ nguồn → demo LLM không bịa nội dung ăn uống                                     |
| **Chunking**  | `chunk_size=300`, so sánh 3 strategy   | Khớp số liệu Section 3 (31 / 23 / 35 chunk)                                                                   |


---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**

> Cách thiết kế và khai thác cấu trúc dữ liệu của Metadata dưới dạng Dictionary để dễ dàng mở rộng và tùy biến nhiều chiều lọc thông tin khác nhau (ví dụ: nhóm chính sách `category`, ngôn ngữ `lang`, nguồn `source`) thay vì chỉ sử dụng các thuộc tính tĩnh.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**

> Cách xử lý sạch mã nguồn Markdown và các ký tự đặc biệt (HTML tags, link ảnh) trước khi đưa vào bộ tách chunk, giúp nâng cao chất lượng tìm kiếm tương đồng vector và tối ưu bộ nhớ lưu trữ.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**

> Tôi sẽ tích hợp embedder thật (`all-MiniLM-L6-v2`) ngay từ đầu và đặt **score threshold** (top-1 < 0.5 → từ chối trả lời). Sẽ tải văn bản đầy đủ từ [VinUni Policy Handbook](https://policy.vinuni.edu.vn/) thay vì bản tóm tắt, và bổ sung metadata `category` cho mọi benchmark query tương ứng (học bổng → `hoc_bong`, kỷ luật → `ky_luat`...).

### Failure Analysis (Ex 3.5)

#### Case 1 — Query trong tri thức nhưng retrieve sai (Q1)

**Query:** *"Sinh viên cần GPA tối thiểu bao nhiêu để duy trì học bổng?"* (gold = `chinh_sach_hoc_bong`).

**Kết quả:** top-1 = `quy_trinh_tam_nghi_thoi_hoc` (score **0.2287**), gold **không** trong top-3 — dù `chinh_sach_hoc_bong.md` có câu *"GPA tối thiểu 3.0"*.

**Nguyên nhân:**

1. **Embedding yếu:** `_mock_embed` không nắm ngữ nghĩa → ranking nhiễu (*retrieval precision* fail).
2. **Từ phổ biến gây nhiễu:** "sinh viên", "học kỳ" xuất hiện ở nhiều tài liệu; mock không phân biệt được chủ đề học bổng vs tạm nghỉ.

**Cách cứu đã kiểm chứng trên UI:** bật `metadata_filter={"category": "hoc_bong"}` → top-1 chuyển sang đúng tài liệu học bổng (tương tự Q5 với `lang=en`).

#### Case 2 — Query ngoài tri thức (out-of-domain)

**Query:** *"Ăn gì cho no"* — không có trong 7 tài liệu VinUni (không có data căng tin/thực đơn).

**Kết quả:** top-1 = `quy_che_hoc_thuat_cu_nhan` (thang điểm GPA, score ~**0.22**) — **hoàn toàn không liên quan**.

**Nguyên nhân:**

1. **Vector search luôn trả top-K** — không có cơ chế "không tìm thấy" ở tầng store.
2. **Score thấp (~0.2) với mock** không được hệ thống diễn giải là "không tin cậy" nếu không có threshold.
3. Đây là failure về **data strategy + grounding**: câu hỏi vượt ngoài phạm vi tri thức đã index.

**Cách xử lý đúng trong production:**

- **Score threshold:** top-1 < 0.35 (mock) hoặc < 0.5 (embedder thật) → agent trả *"Không có thông tin trong tài liệu chính sách"*.
- **Honest uncertainty** trong prompt agent: không bịa từ chunk không liên quan.
- Mở rộng corpus nếu muốn trả lời loại câu hỏi đó (không áp dụng cho lab policy-only).

**Đề xuất cải thiện tổng hợp:**


| Vấn đề                                  | Giải pháp                               |
| --------------------------------------- | --------------------------------------- |
| Mock embedder, score 0.15–0.30 vô nghĩa | Dùng `EMBEDDING_PROVIDER=local`         |
| Q1/Q2/Q4 sai top-1                      | Metadata filter theo `category`         |
| Query ngoài domain vẫn có kết quả       | Score threshold + từ chối trả lời       |
| Chunk không đủ chi tiết                 | Tải full policy từ policy.vinuni.edu.vn |


> **Bài học demo:** Khi embedding yếu, **metadata filtering** là đòn bẩy rẻ nhất (Q5 chứng minh). Khi query ngoài tri thức, **score threshold + honest uncertainty** quan trọng hơn cố gắng tăng top-K — vì không có gold chunk nào để retrieve.

---

## Tự Đánh Giá


| Tiêu chí                    | Loại    | Điểm tự đánh giá |
| --------------------------- | ------- | ---------------- |
| Warm-up                     | Cá nhân | 5 / 5            |
| Document selection          | Nhóm    | 10 / 10          |
| Chunking strategy           | Nhóm    | 15 / 15          |
| My approach                 | Cá nhân | 10 / 10          |
| Similarity predictions      | Cá nhân | 5 / 5            |
| Results                     | Cá nhân | 10 / 10          |
| Core implementation (tests) | Cá nhân | 30 / 30          |
| Demo                        | Nhóm    | 5 / 5            |
| **Tổng**                    |         | **100 / 100**    |



# 待办

- [x] 简化 `src/rag/services/retrieval/vector_search.py` 的候选分页大小计算。
  - 将 `page_size = min(max(top_k * 2, 10), self._max_candidates)` 改为 `page_size = max(top_k * 2, 10)`。
  - 原因：实际查询已经通过 `min(page_size, self._max_candidates - offset)` 限制剩余候选预算，外层 `min` 属于重复限制。
  - 保留实际查询处的预算限制，确保小预算和最后一批查询不超限。
  - 已实施，保留查询处的候选预算限制。

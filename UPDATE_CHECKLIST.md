# listed-company-analysis Skill 更新清单

## ✅ 已完成

### 1. 行业分析模块重构
- **问题**：原 `industry_analysis.py` 因沙箱网络限制无法直接联网搜索
- **解决**：新建 `industry_analysis_v2.py`，采用 AI驱动两步式工作流
  - 第一步：输出搜索任务（JSON格式）
  - 第二步：AI用 online-search 搜集数据
  - 第三步：生成完整行业研究报告

### 2. research_workflow.py 更新
- 更新 `run_industry_analysis()` 函数
- 新增 `search_results` 参数，支持AI传入搜索数据
- 未提供数据时返回搜索任务清单

### 3. SKILL.md 更新
- 新增 AI驱动版行业分析使用说明
- 保留原有功能文档

---

## ⚠️ 待处理

### 1. 旧版文件清理
- `scripts/industry_analysis.py` — 编码已损坏，建议删除或重命名为 `_deprecated`
- 保留 `scripts/industry_analysis_v2.py` 作为正式版本

### 2. 临时/调试文件清理
以下为开发过程中的调试/探测脚本，可考虑清理：
```
scripts/hkex_pw_*.py (6个文件) — 港股搜索调试
scripts/hkex_jsf_*.py (3个文件) — 港股JSF调试
scripts/*_probe_*.py (8个文件) — API探测
scripts/*_patch*.py (5个文件) — 修复脚本
scripts/*_debug*.py (3个文件) — 调试脚本
scripts/*_test*.py (多个) — 测试脚本
scripts/*_recover*.py (2个文件) — 恢复脚本
scripts/*_rewrite*.py (1个文件) — 重写脚本
scripts/*_fix*.py (3个文件) — 修复脚本
scripts/*_inspect*.py (1个文件) — 检查脚本
scripts/*_find*.py (1个文件) — 查找脚本
scripts/explore_*.py (3个文件) — 探索脚本
```

建议：移至 `scripts/_deprecated/` 或直接删除

### 3. output 目录清理
- 测试输出文件夹：`output/trace_*_test/`、`output/test_*/`、`output/*_test/`
- 旧报告：保留近期7天的，删除更早的

### 4. requirements.txt 更新
- 确认依赖列表是否完整
- 当前未发现此文件，建议创建

### 5. 测试覆盖
- `tests/test_core.py` 已存在
- 建议增加 `industry_analysis_v2` 的单元测试

---

## 📋 建议操作

### 立即执行

```bash
# 1. 删除旧版行业分析（编码已损坏）
rm scripts/industry_analysis.py

# 2. 清理调试脚本
mkdir -p scripts/_deprecated
mv scripts/hkex_pw_*.py scripts/_deprecated/
mv scripts/hkex_jsf_*.py scripts/_deprecated/
mv scripts/*_probe*.py scripts/_deprecated/
mv scripts/*_patch*.py scripts/_deprecated/
mv scripts/*_debug*.py scripts/_deprecated/
mv scripts/*_fix*.py scripts/_deprecated/
mv scripts/*_recover*.py scripts/_deprecated/
mv scripts/*_rewrite*.py scripts/_deprecated/
mv scripts/*_inspect*.py scripts/_deprecated/
mv scripts/explore_*.py scripts/_deprecated/

# 3. 清理测试输出
rm -rf output/trace_*_test output/test_* output/*_test
```

### 后续优化

1. **创建 requirements.txt**（如需要）
2. **增加行业分析 v2 的测试用例**
3. **统一编码处理**：确保所有脚本使用 UTF-8
4. **文档完善**：更新 MEMORY.md 中的 Skill 使用说明

---

## 文件统计

| 类别 | 数量 | 建议 |
|------|------|------|
| 核心分析模块 | ~20 | 保留 |
| 调试/临时脚本 | ~40 | 移至 _deprecated |
| 测试输出 | ~15个文件夹 | 删除 |
| 正式输出 | ~10个文件夹 | 保留 |

---

*生成时间: 2026-04-28 18:20*

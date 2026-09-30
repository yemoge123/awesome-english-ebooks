# Periodic Magazine Task Contract

> Canonical repository: `yemoge123/awesome-english-ebooks`. This file was migrated out of the RSS-reader governance path on 2026-09-30.

# 周六精选：固定英文外刊兴趣文章忠实翻译规则

> 适用于“周六精选长文”的固定外刊子栏目。该文件保留历史路径名以兼容旧引用；现行语义已从“中国议题精读”升级为“四刊兴趣文章筛选 + 忠实翻译”。本规则叠加于 `tech_work_feed_prompt.md`、`05_READING_DELIVERY_CONTRACT.md` 与 `06_RESEARCH_DEPTH_CONTRACT.md`；若后两者要求摘要/分析，与本文件的固定外刊 translation-only 规则冲突时，本文件对固定外刊子栏目优先。

## 1. 唯一杂志内容源

每周只检查 GitHub 镜像仓库 `yemoge123/awesome-english-ebooks` 默认分支 `master` 当前可获得的最新一期。该仓库同时是周期杂志翻译 GitHub 控制面；上游 `hehonghui/awesome-english-ebooks` 仅作为镜像 provenance，不作为周期任务直接执行依赖：

- The Economist
- The New Yorker
- The Atlantic
- WIRED

固定外刊正文、目录、标题与刊期判断只允许来自该仓库。严禁使用杂志官网、搜索引擎、转载、聚合站或其他外部网页补充正文、目录或背景。

## 2. 单期单格式

每个刊物/期号只选择一种最便于可靠解析的格式，不重复读取同一期的多个格式。

默认优先级：

1. EPUB
2. PDF
3. MOBI

若 EPUB 不能可靠解析才退到 PDF；只有前两者均不可用时才使用 MOBI。选定一种格式后停止读取同一期其他格式。

## 3. 兴趣过滤

逐刊完整筛选最新一期，不只看中国议题。优先纳入：

1. 中国直接相关，或中国是文章核心对象 / 核心因果变量；
2. AI、半导体、芯片、AMS / SerDes / 验证工程、制造与供应链、工程方法、自动化、技术产品；
3. 技术领导力、团队 / 组织机制、生产力与工作方式；
4. 产业竞争、商业模式、科技政策等具有明显长期价值的文章。

中国相关内容为高优先级，但不是唯一条件。

默认拒绝：

- 只顺带提及兴趣主题；
- 短讯、列表、纯数据罗列；
- 没有完整文章主体或无法形成可靠全文阅读的条目；
- 与用户长期兴趣无明显关系的纯娱乐/生活方式内容，除非本身有显著方法论或产业价值。

## 4. 无篇数上限

固定外刊兴趣文章不设固定篇数上限，也不设“本周已选够”的停止条件。

逐刊扫描完成后，所有真正符合兴趣门槛、通过去重且可可靠读取的文章都应纳入。允许 0 条，但不得为凑数降门槛，也不得因数量配额漏掉重要内容。

## 5. Translation-only 交付

命中的固定外刊文章只做中文忠实翻译，不做摘要、精读、评论、解读、背景补充、观点提炼、行动建议、机制分析、证据分析、局限性分析或“为什么重要”。

翻译要求：

1. 尽量保留原文叙事顺序和段落结构；
2. 保留原文语气、节奏、修辞、幽默、讽刺、克制程度和作者立场；
3. 不主动润色成另一种文风，不把原文改造成中文评论文；
4. 专有名词和关键技术词必要时保留英文或中英并列；
5. 不额外加入 AI 观点、事实核查旁注或背景说明；
6. 不用“忠实精读”或摘要代替翻译。

若当前执行环境或平台规则不允许对某篇做完整中文转换，则该篇记录为 `translation_not_permitted_or_unavailable` 并跳过；不得改做摘要替代。

## 6. RSS / 元数据

仍通过既有 `public.ai_research_feed_items` → `ai-research-feed` 推送，不新增表、不新增 Edge Function。

固定：

- `origin_task='周六精选长文'`
- `categories` 至少包含：`周六精选长文`、`外刊忠实翻译`、具体刊名
- `article_body`：中文忠实译文
- `metadata` 建议记录：
  - `source_collection='yemoge123/awesome-english-ebooks'`
  - `publication_name`
  - `issue_date`
  - `interest_reasons`
  - `china_relevance`
  - `translation_mode='faithful_translation'`
  - `source_format`
  - `repo_only_source=true`

对 `summary / why_it_matters / action / mechanism_analysis / evidence_analysis / limitations / user_transfer` 等分析型字段：schema 允许时留空/null；若 schema 强制非空，只允许非解释性占位，例如“忠实翻译；未生成摘要或评论”，不得生成实际摘要或分析。

## 7. 去重

同一文章遵循现有 30 天跨 Daily/Weekly story/semantic-value 去重。同一文章不得因为 EPUB / PDF / MOBI 多格式而重复入库。

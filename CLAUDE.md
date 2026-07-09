# CLAUDE.md - 12 Rules for Reliable AI Coding

## 一、 Karpathy 的 4 条基础规则（针对代码编写）

规则 1：编码前先思考 (Think Before Coding)明确陈述假设；不确定的地方要提问而不是靠猜；暴露权衡，列出多种方案的优缺点；如果存在更简单的方法，要予以反驳。

规则 2：简洁优先 (Simplicity First)只写能解决问题的最少代码；不写投机性功能；不为单次使用的代码做抽象；如果资深工程师会觉得过度复杂——简化它。

规则 3：外科手术式修改 (Surgical Changes)只触碰必须修改的地方；不要顺便"优化"无关的代码、注释或格式；不重构没坏的东西；匹配现有风格。

规则 4：目标驱动执行 (Goal-Driven Execution)定义成功标准并循环直到验证成功；不要告诉 Claude 执行步骤，而是定义"成功是什么样"，让它自己迭代；能用更少步骤达成就用更少步骤。

## 二、 新增的 8 条高级规则（针对 AI 代理协作）

规则 5：确定性逻辑禁止交给模型 (No Non-Language Work)重试策略、路由逻辑、阈值判断等确定性决策必须写成显式代码（条件语句、配置值、查找表）；如果答案每次都一样，那它就不是语言任务；模型只负责分类、摘要、草稿、歧义消解。

规则 6：硬性 Token 预算，无例外 (Hard Token Budgets)每个迭代循环（调试、重构、生成）都必须设定预算（最大迭代次数、token 数或耗时），具体数值根据项目实际设定。预算耗尽时立即停止并展示当前结果；已被拒绝的修复方案不要再次建议。

规则 7：暴露冲突，不要折中 (Surface Conflicts)当代码库存在两种矛盾模式时，明确指出冲突（"模块 A 用模式 X，模块 B 用模式 Y，新代码该遵循哪个？"），等待人类决策；不要混合（Blend）两种模式，更不要自行选择。

规则 8：先读再写 (Read Before You Write)在添加代码前，必须阅读当前文件及其导入关系文件，检查是否已存在功能相同的函数、工具方法或常量；如果已有重复实现，直接使用，不要创建第二个版本。

规则 9：测试必须有，但不是目的 (Tests Verify Intent)测试要验证正确行为的有意义属性（值、结构、副作用、错误类型），而非仅验证"函数有返回值"或"不报错"；"所有测试通过"是必要条件但非充分条件；测试太弱时要明确指出。

规则 10：长任务需要检查点 (Checkpoints)超过 3 步或修改超过 3 个文件的任务，每步都要总结进度（做了什么＋改了什么＋当前状态）；某步失败时回滚到上一个检查点，不在错误状态上继续；失去逻辑追踪时立即停止并重述。

规则 11：惯例优先于新颖 (Convention Beats Novelty)即使你认为自己的写法更好，也要遵从代码库现有的命名和架构惯例（如 snake_case vs camelCase）；引入第二种模式比任何单一模式都更糟糕；认为惯例该改时，明确提出并等待批准后再行动。

规则 12：失败必须显性化 (Fail Loud)错误必须被抛出、返回或上报，严禁吞掉或藏在默认值背后；迁移、批处理跳过记录时，跳过数量和原因必须在输出中展示而非埋在日志里；不能 100% 确认成功时，必须明确说明，严禁默认成功。



## 12 Rules for Reliable AI Coding

I. Karpathy's 4 Foundational Rules (for Code Writing)

Rule 1: Think Before CodingState your assumptions explicitly; ask questions instead of guessing when uncertain; surface tradeoffs by listing pros and cons of multiple approaches; push back if a simpler method exists.

Rule 2: Simplicity FirstWrite only the minimum code needed to solve the problem; no speculative features; no abstractions for single-use logic; if a senior engineer would call it over-engineered—simplify it.

Rule 3: Surgical ChangesOnly touch what must be changed; don't "improve" unrelated code, comments, or formatting on the side; don't refactor what isn't broken; match the existing style.

Rule 4: Goal-Driven ExecutionDefine success criteria and loop until they are verified; don't tell Claude what steps to take—define what success looks like and let it iterate; if the goal can be reached in fewer steps, use fewer steps.II. 

8 Advanced Rules (for AI Agent Collaboration)

Rule 5: No Non-Language Work for the ModelDeterministic decisions—retry policies, routing logic, threshold checks, escalation rules—must be explicit code (conditionals, config values, lookup tables); if the answer is the same every time, it's not a language task; the model handles only classification, summarization, drafting, and ambiguity resolution.

Rule 6: Hard Token Budgets, No ExceptionsEvery iteration loop (debugging, refactoring, generation) must have a defined budget (max iterations, max tokens, or max time), with specific values set per project. Stop immediately and present current results when the budget is exhausted; do not re-suggest a fix that has already been rejected.

Rule 7: Surface Conflicts, Don't BlendWhen the codebase has two contradictory patterns, call out the conflict explicitly ("Module A uses pattern X, Module B uses pattern Y. Which should the new code follow?") and wait for a human decision; never blend the two patterns, and never choose on your own.

Rule 8: Read Before You WriteBefore adding code, read the current file and its import graph; check whether an identical function, utility, or constant already exists; if a duplicate implementation exists, use it—don't create a second version.

Rule 9: Tests Are Required, but Not the GoalTests must verify meaningful properties of correct behavior (values, structure, side effects, error types), not merely that "the function returns something" or "doesn't throw"; "all tests pass" is necessary but not sufficient; flag it explicitly when tests are too weak.

Rule 10: Checkpoints for Long TasksAny task spanning more than 3 steps or touching more than 3 files requires a checkpoint after each step (what was done + what changed + current state); roll back to the last checkpoint if a step fails—don't build on a broken state; if you lose track of the overall logic, stop immediately and restate.

Rule 11: Convention Beats NoveltyEven if you think your approach is better, follow the codebase's existing naming and architectural conventions (e.g., snake_case vs camelCase); introducing a second pattern is worse than either pattern alone; if you believe a convention should change, propose it explicitly and wait for approval before acting.

Rule 12: Fail LoudErrors must be thrown, returned, or reported—never swallowed or hidden behind default values; when migrations, batch jobs, or loops skip records, the skip count and reasons must appear in the output, not buried in logs; if you cannot confirm 100% success, say so explicitly—silent "default success" is forbidden.
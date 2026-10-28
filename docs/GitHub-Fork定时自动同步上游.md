# GitHub Fork 定时自动同步上游完全指南

> 2026-10-28 会话沉淀。场景：把第三方开源项目 fork 到自己账号，并让 fork 每天自动跟上游保持同步。全程只用 GitHub REST API（沙盒无 curl、git+https 被墙）。

## 一、Fork 操作（纯 API）

```
POST /repos/{上游owner}/{repo}/forks        body: {"default_branch_only": false}
```

- 返回 **202** = 异步创建中，需轮询 `GET /repos/{自己}/{repo}` 直到 200（一般几秒~1分钟）
- 返回 403+`name already exists on this account` = **命名冲突**：GitHub 同一账号下仓库路径唯一，fork 任何同名仓库前必须先删掉旧的
- 删除是**不可逆破坏性操作**：`DELETE /repos/{owner}/{repo}`（204 成功），旧 fork 上的自定义分支/issue/star 全部消失，操作前务必与用户确认
- 鉴别"同名但不同上游"：`GET /repos/{owner}/{repo}` 看 `parent.full_name`；独立仓库 `fork:false`

## 二、自动同步工作流（放 fork 仓库里）

文件 `.github/workflows/sync-upstream.yml`，要点：

1. **双触发**：`schedule`（cron）+ `workflow_dispatch`（手动，带 `force` 输入做硬同步兜底）
2. **cron 是 UTC**：北京时间 = UTC+8，如 `'33 1 * * *'` = 每天北京时间 09:33
3. **必须声明权限**：`permissions: contents: write`，否则 `GITHUB_TOKEN` 推不动
4. **首选官方 merge-upstream API**（能 fast-forward 就 ff，有新提交会 merge）：

```yaml
- run: |
    curl -s -X POST \
      -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
      "https://api.github.com/repos/$GITHUB_REPOSITORY/merge-upstream" \
      -d '{"branch":"main"}'
```

   返回 200/202=已同步；**409=分叉/冲突**（fork 上有自己的提交且与上游冲突）
5. **兜底硬同步**（仅手动选 force=true）：`git clone --depth 1` + `git remote add upstream` + `git fetch` + `git reset --hard upstream/分支` + `git push --force`，放弃 fork 上所有差异
6. 上游若自带 `.github/workflows`，fork 会继承；**Actions 默认在 fork 上是开启的**，但仍建议 `PUT /repos/{repo}/actions/permissions {"enabled":true,"allowed_actions":"all"}` 显式确认

## 三、验证闭环（不能只看 dispatch 204）

1. 触发测试：`POST /repos/{repo}/actions/workflows/sync-upstream.yml/dispatches {"ref":"主分支"}`（204=已受理）
2. 轮询 `GET /repos/{repo}/actions/runs?per_page=1` 等 `status=completed`，看 `conclusion=success`
3. **核验 fork 与上游真实一致**：
   - `GET /repos/{fork}/branches/{br}` 与 `GET /repos/{upstream}/branches/{br}` 比对 commit sha
   - 或 `GET /repos/{fork}/compare/{br}...{owner}:{br}` 看 ahead/behind
   - **判读陷阱**：刚推完工作流后 fork 必然 `behind:1`——那 1 个提交就是工作流本身；只要 `ahead:0` 就说明上游提交无缺失，属正常状态，不是同步失败

## 四、环境坑（本沙盒实测）

- 无 `curl`/`crontab`/cron 守护进程 ⇒ 定时只能靠 GitHub Actions，API 调用用 `python3 + urllib.request`
- Token 权限看响应头 `X-OAuth-Scopes`（fork 需 `repo`，删库需 `delete_repo`）
- Contents API 中文路径必须 `urllib.parse.quote(path, safe='')` 逐字符转义
- PUT contents 已存在文件必须带旧 `sha`（GET contents 拿），否则 422

## 五、本次交付实例

| fork | 上游 | 主分支 | 每日同步(北京) |
|---|---|---|---|
| a534008561/ZakoProxyCLI | mizaawa/ZakoProxyCLI | main | 09:17 |
| a534008561/dsh-purge | YuJunZhiXue/dsh-purge | master | 09:33 |

两仓库手动 dispatch 测试 conclusion=success，与上游 ahead:0 确认同步链路真实可用。

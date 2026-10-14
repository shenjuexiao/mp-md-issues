# 公众号文章提取转发

## 🚀 项目链接 

[shenjuexiao/mp-md-issues](https://github.com/shenjuexiao/mp-md-issues)

## 😀 一句话介绍

填写文章标题、发布时间、链接，工作流提取公众号文章，转化为 Markdown 格式，存储并发布 Issues，可以同步新增、修改、删除。

## 📝 文件目录

### /
- `mp-readme.md`：填写文章标题、发布时间、链接
- `mp_md/`：存储 `发布时间_文章标题.md`

### .github/workflows/
- `mp-md-issues.yml`：工作流

### scripts/
- `detect_changes.py`：检测 `mp-readme.md` 相对上次提交变化
- `mp_extract.py`：提取公众号文章转 Markdown 存储
- `mp_issue_create.py`：新增文章创建 Issues，标签 MP
- `mp_issue_update.py`：修改后更新 Issues
- `mp_issue_delete.py`：删除 `mp-readme.md` 行后，删除 Issues

# Publish from a Linux terminal

## 1. Test locally

```bash
python3 -m unittest discover -s tests -v
python3 cli/arena.py validate --kind ai --file examples/ai-workflow.json
python3 cli/arena.py validate --kind kubernetes --file examples/kubernetes-job.yaml
```

## 2. Initialize Git

```bash
git init
git branch -M main
git add .
git status
git commit -m "Initial public protected workflow arena"
```

Before committing, confirm no `.env` file or credential is staged.

## 3. Create the public GitHub repository

With GitHub CLI:

```bash
gh repo create protected-workflow-arena \
  --public \
  --source=. \
  --remote=origin \
  --push
```

## 4. Verify visibility

```bash
gh repo view --json nameWithOwner,visibility,url
```

Confirm:

```text
"visibility": "PUBLIC"
```

## 5. Share

Print the repository URL:

```bash
gh repo view --json url --jq '.url'
```

Share that URL with tools or developers that need the public client.

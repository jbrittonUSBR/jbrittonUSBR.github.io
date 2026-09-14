# Daily News Updates

GitHub Pages site for `jbrittonUSBR`.

Live URL after Pages is enabled:

https://jbrittonUSBR.github.io

## Create the repository

1. On GitHub, create a **public** repository named exactly:

   `jbrittonUSBR.github.io`

2. Upload these files to the `main` branch (or clone, copy them in, and push).

3. In the repo: **Settings → Pages**
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/ (root)`
   - Save

Wait a minute or two, then open https://jbrittonUSBR.github.io

## Add a daily post

Create `_posts/YYYY-MM-DD-short-title.md` with:

```markdown
---
layout: post
title: "September 15 notes"
date: 2026-09-15 08:00:00 -0600
categories: news
---

Your update here.
```

Commit to `main`. The home page lists posts newest first.

## Optional: preview locally

Requires Ruby and Bundler.

```bash
bundle install
bundle exec jekyll serve
```

Then open http://localhost:4000

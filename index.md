---
layout: default
title: Home
---

<div class="briefing">
  <p class="kicker">Priority Headlines</p>
  <h1>Today’s notes</h1>
  <p class="lede">Short daily briefing. Newest file first.</p>
</div>

{% assign latest = site.posts.first %}
{% if latest %}
<article class="latest">
  <p class="meta">{{ latest.date | date: "%A, %d %B %Y" }}</p>
  <h2><a href="{{ latest.url | relative_url }}">{{ latest.title }}</a></h2>
  <p><a class="button" href="{{ latest.url | relative_url }}">Open today’s file</a></p>
</article>
{% endif %}

<h3>Archive</h3>
{% assign years = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
<ul class="year-list">
{% for year in years %}
  <li><a href="{{ year.name | prepend: '/' | relative_url }}">{{ year.name }}</a></li>
{% endfor %}
</ul>

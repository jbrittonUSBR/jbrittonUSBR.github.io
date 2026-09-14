---
layout: default
title: Daily News
---

{% assign years = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
<ul>
{% for year in years %}
  <li><a href="{{ year.name | prepend: '/' | relative_url }}">{{ year.name }}</a></li>
{% endfor %}
</ul>

---
layout: default
title: Daily News
---

{% assign posts_by_year = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
{% for year in posts_by_year %}
## {{ year.name }}
{% assign posts_by_month = year.items | group_by_exp: "post", "post.date | date: '%B'" %}
{% for month in posts_by_month %}
### {{ month.name }}
<ul>
{% for post in month.items %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
  </li>
{% endfor %}
</ul>
{% endfor %}
{% endfor %}

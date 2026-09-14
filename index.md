---
layout: default
title: Daily News
---

{% assign posts_by_year = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
{% for year in posts_by_year %}
## {{ year.name }}
{% assign posts_by_month = year.items | group_by_exp: "post", "post.date | date: '%Y-%m'" %}
{% for month in posts_by_month %}
### {{ month.items.first.date | date: "%B" }}
{% assign posts_by_day = month.items | group_by_exp: "post", "post.date | date: '%d'" %}
<ul>
{% for day in posts_by_day %}
  <li>
    {{ day.name }}
    <ul>
    {% for post in day.items %}
      <li><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
    {% endfor %}
    </ul>
  </li>
{% endfor %}
</ul>
{% endfor %}
{% endfor %}

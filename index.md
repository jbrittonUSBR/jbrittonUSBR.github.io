---
layout: default
title: Home
---

<div class="briefing">
  <h1>Daily Brief</h1>
  <p class="lede">Short daily briefing. Newest file first.</p>
</div>

{% assign latest = site.posts.first %}
{% if latest %}
<article class="latest">
  <p class="meta">{{ latest.date | date: "%A, %d %B %Y" }}</p>
  <h2><a href="{{ latest.url | relative_url }}">{{ latest.title }}</a></h2>
</article>

<h3>Daily Brief Archive</h3>
{% assign years = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
<ul class="year-list">
{% for year in years %}
  <li><a href="{{ year.name | prepend: '/' | relative_url }}">{{ year.name }}</a></li>
{% endfor %}
</ul>
{% endif %}

<div class="briefing">
  <h1>First Alert</h1>
</div>
<p><a href="{{ '/first-alert/' | relative_url }}">Open Today's Critical Infrastructure Brief</a></p>

<p><a href="{{ '/first-alert/map/' | relative_url }}">First Alert incident map</a></p>
<iframe
  title="First Alert map"
  src="{{ '/first-alert/embed/' | relative_url }}"
  style="width:100%;height:420px;border:1px solid #ddd4c4;border-radius:4px;"
  loading="lazy"></iframe>
 
 <div class="briefing"> 
  <h1>Source List for Daily Brief</h1>
  <p class="lede">Chicago Style citation list with links to the articles.</p>
</div> 
{% assign src_pages = site.pages | where_exp: "p", "p.url contains '/sources/'" | sort: "url" | reverse %}
{% assign latest_src = src_pages.first %}
{% if latest_src %}
<article class="latest">
  <p class="meta">{{ latest_src.title | replace: "Sources — ", "" }}</p>
  <h2><a href="{{ latest_src.url | relative_url }}">{{ latest_src.title | replace: "Sources", "Bibliography" }}</a></h2>
</article>
{% endif %}

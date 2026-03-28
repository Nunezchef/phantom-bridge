### bridge_sitemap:

shows learned URL patterns from browser navigation — which pages the user has visited, grouped by domain and feature area
optional `domain` argument to filter to a single domain; omit to see all domains
use this to understand what areas of a web app the user has explored, before attempting to navigate or automate
sitemaps are built automatically while the bridge is running — no setup needed

usage:
```json
{
  "thoughts": ["Let me check what pages the user has visited on toast.restaurant.com to understand the app structure"],
  "headline": "Checking learned sitemap for Toast",
  "tool_name": "bridge_sitemap",
  "tool_args": {
    "domain": "toast.restaurant.com"
  }
}
```

```json
{
  "thoughts": ["I want to see all domains the user has browsed to find which services they use"],
  "headline": "Listing all learned sitemaps",
  "tool_name": "bridge_sitemap",
  "tool_args": {}
}
```

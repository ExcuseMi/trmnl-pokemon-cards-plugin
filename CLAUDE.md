# trmnl-pokemon-cards-plugin

Let's make this a pokemon only plugin again:

Have an Art ony option.
x:44, y:87
w:503 , h:321
Maybe we can do that via an SVG that uses the image and the crops out the rest.

Make sure we have the mashup layout like /home/excuseme/workspace/trmnl-inaturalist-plugin/plugin, rework the whole plugin.
If not art mode, we show 2 columns: image + stats if we have the horizontal space. Else just the card.
It would nice if we show the logo or a booster pack image of the series it was in.
Optional: Maybe the value as well if we have that data.
Rework the whitelisting again according to the update trmnl skill.
Rework the redis integration
Make sure our dependencies version are ok.

Goals of the plugin:
- Explore current packs to find out what's in them aka which pack should I buy
- Explore the rares / prettiest cards, nice for the art only view.
- More advanced is filtering per series, maybe xhrselect for that.

Limitations:
Be gently on the API, maybe we can grab a bunch of cards per filter combination every hour?
Maybe we could store all data forever? Is that possible? What does it cost?
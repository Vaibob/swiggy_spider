import scrapy
import pandas as pd
import time

class SwiggySpider(scrapy.Spider):
    name = 'swiggy'
    start_urls = ['https://www.swiggy.com/']
    restaurant_data = []
    seen_urls = set()
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RETRY_HTTP_CODES': [403], 
        'RETRY_TIMES': 5, 
    }

    def parse(self, response):
        city_links = response.css('div#city-links a._3TjLz.b-Hy9::attr(href)').getall()

        for city_link in city_links:
            city_url = response.urljoin(city_link)
            city_name = city_link.split('/')[-1]
            yield scrapy.Request(city_url, callback=self.parse_city, meta={'city_name': city_name})

    def parse_city(self, response):
        city_name = response.meta['city_name']
        restaurant_divs = response.css('a.RestaurantList__RestaurantAnchor-sc-1d3nl43-3.kcEtBq')

        for restaurant_div in restaurant_divs:
            restaurant_url = response.urljoin(restaurant_div.css('::attr(href)').get())
            restaurant_name = restaurant_div.css('.sc-beySbM.cwvucc::text').get()
            restaurant_rating = restaurant_div.css('.sw-restaurant-card-subtext-container .sc-beySbM.fTVWWG::text').get()
            restaurant_cuisines = restaurant_div.css('.sw-restaurant-card-descriptions-container .sc-beySbM.iTWFZi:nth-child(1)::text').get()
            restaurant_locality = restaurant_div.css('.sw-restaurant-card-descriptions-container .sc-beySbM.iTWFZi:nth-child(2)::text').get()

            if restaurant_url not in self.seen_urls:
                self.seen_urls.add(restaurant_url)
                initial_data = {
                    'city_name': city_name,
                    'restaurant_url': restaurant_url,
                    'restaurant_name': restaurant_name,
                    'restaurant_cuisines': restaurant_cuisines,
                    'restaurant_locality': restaurant_locality,
                    'restaurant_rating': restaurant_rating,
                }

                yield scrapy.Request(restaurant_url, callback=self.parse_restaurant, meta={'initial_data': initial_data}, errback=self.errback_httpbin)

    def parse_restaurant(self, response): 
        if response.status == 200:
            initial_data = response.meta['initial_data']
            cost_for_two = response.css('li.RestaurantTimeCost_item__2HCUz span::text').get()
            count_of_ratings = response.css('button.RestaurantRatings_wrapper__2294i span.RestaurantRatings_totalRatings__3d6Zc::text').get()
            offers = response.css('.RestaurantOffer_header__3FBtQ::text').getall()
            offers = '; '.join(offers)

            initial_data.update({
                'cost_for_two': cost_for_two,
                'count_of_ratings': count_of_ratings,
                'id': len(self.restaurant_data) + 1,
                'offers': offers
            })

            self.restaurant_data.append(initial_data)
        elif response.status == 403:
            self.log("Received 403 status code. Pausing...")
            time.sleep(60)  
            yield scrapy.Request(response.url, callback=self.parse_restaurant, meta=response.meta, dont_filter=True)
        else:
            self.log(f"Received non-200 status code: {response.status}")

    def errback_httpbin(self, failure): # this method will be called whenever there are errors
        self.log(repr(failure))

    def closed(self, reason):
        df = pd.DataFrame(self.restaurant_data)
        df = df.sort_values('id')

        # Reorder the columns to make 'id' the first column
        columns = ['id'] + [col for col in df.columns if col != 'id']
        df = df[columns]

        df.to_csv('restaurant_data.csv', index=False)


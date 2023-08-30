import requests
import csv
import json

def fetch_data(lat, lng, offset):
    url = "https://www.swiggy.com/dapi/restaurants/list/update"
    payload = {
        "lat": lat,
        "lng": lng,
        "nextOffset": "COVCELQ4KICA38rDsq36ZjCnEzgD",
        "widgetOffset": {
            "collectionV5RestaurantListWidget_SimRestoRelevance_food_seo": str(offset),
        },
        "filters": {},
        "seoParams": {
            "seoUrl": "https://www.swiggy.com/",
            "pageType": "FOOD_HOMEPAGE",
            "apiName": "FoodHomePage"
        },
        "page_type": "DESKTOP_WEB_LISTING",
        "_csrf": "PQ9djvYTyhnX-ovwRLrEQcRFsGQ9cnhu2UMq"
    }
    headers = {
        "content-type": "application/json",
        "origin": "https://www.swiggy.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    response = requests.post(url, json=payload, headers=headers)
    card_data = response.json().get('data', {}).get('cards', [])
    
    if card_data:
        restaurant_list = card_data[0].get('card', {}).get('card', {}).get('gridElements', {}).get('infoWithStyle', {}).get('restaurants', [])
        return restaurant_list
    return []

global_id = 1  # Initialize a global ID counter at the top of your script

def write_to_csv(data, city, header_written):
    global global_id  # Declare the variable as global so we can modify it
    mode = 'a' if header_written else 'w'
    with open('output.csv', mode, newline='') as csvfile:
        fieldnames = ['ID', 'City', 'Restaurant Name', 'Area Name', 'Cost for Two', 'Cuisines', 'Average Rating', 'Total Ratings', 'Is Open', 'Next Close Time', 'Aggregated Discount Info', 'Restaurant Link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not header_written:
            writer.writeheader()
        
        for idx, restaurant in enumerate(data, global_id):
            info = restaurant.get('info', {})
            cta = restaurant.get('cta', {})
            
            writer.writerow({
                'ID': idx,
                'City': city,
                'Restaurant Name': info.get('name'),
                'Area Name': info.get('areaName'),
                'Cost for Two': info.get('costForTwo'),
                'Cuisines': ', '.join(info.get('cuisines', [])),
                'Average Rating': info.get('avgRating'),
                'Total Ratings': info.get('totalRatingsString'),
                'Is Open': info.get('isOpen'),
                'Next Close Time': info.get('availability', {}).get('nextCloseTime'),
                'Aggregated Discount Info': info.get('aggregatedDiscountInfoV3', {}).get('header'),
                'Restaurant Link': cta.get('link')
            })
        
        global_id = idx + 1  

def get_combined_place_info(city_names):
    autocomplete_url = "https://www.swiggy.com/dapi/misc/place-autocomplete"
    recommend_url = "https://www.swiggy.com/dapi/misc/address-recommend"
    headers = {
        "cookie": "__SW=0Uay9uyKvcEViU3CIOCxlH7EfbhOtz1m; _guest_tid=686a8794-a9eb-4502-839e-715baeabd2ee; _device_id=960218be-5442-067d-8f1b-9ea4569623f7; _sid=91t69907-70bd-4fc5-a456-b70cca5b3334",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    
    result_data = []

    for city_name in city_names:
        autocomplete_query = {"input": city_name, "types": ""}
        autocomplete_response = requests.get(autocomplete_url, headers=headers, params=autocomplete_query)
        
        if autocomplete_response.status_code == 200:
            autocomplete_data = autocomplete_response.json()
            if autocomplete_data.get("statusCode") == 0 and "data" in autocomplete_data:
                place_info = autocomplete_data["data"][0]
                place_id = place_info["place_id"]
                
                print(f"City: {city_name}")
                print(f"Place ID: {place_id}")
                print("-" * 30)
                
                recommend_query = {"place_id": place_id}
                recommend_response = requests.get(recommend_url, headers=headers, params=recommend_query)
                
                if recommend_response.status_code == 200:
                    recommend_data = recommend_response.json()
                    if recommend_data.get("statusCode") == 0 and "data" in recommend_data:
                        for recommend_info in recommend_data["data"]:
                            city_data = {
                                "city_name": city_name,
                                "place_id": place_id,
                                "lat": recommend_info["geometry"]["location"]["lat"],
                                "lng": recommend_info["geometry"]["location"]["lng"],
                                "formatted_address": recommend_info["formatted_address"]
                            }
                            result_data.append(city_data)

    return result_data

if __name__ == "__main__":
    city_names = ["Pune","Mumbai", "Delhi", "Bangalore"]
    place_info_list = get_combined_place_info(city_names)
    
    header_written = False
    num_scrolls = 10 # We can adjust the number of scrolls as per our requirement

    for place_info in place_info_list:
        lat = place_info['lat']
        lng = place_info['lng']
        city = place_info['city_name']
        
        for i in range(num_scrolls):
            print(f"Fetching data for {city}, scroll number {i+1}")
            offset = i * 25  # We can adjust offset as per our requirement
            restaurant_list = fetch_data(lat, lng, offset)
            if restaurant_list:
                write_to_csv(restaurant_list, city, header_written)
                header_written = True

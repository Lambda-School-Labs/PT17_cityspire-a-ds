import requests
import os
import datetime
import json
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, BaseSettings, SecretStr
from app.ml import City, validate_city
from app.state_abbr import us_state_abbrev as abbr
from dotenv import dotenv_values, load_dotenv
import pprint

router = APIRouter()
load_dotenv()


weather_api = os.getenv("WEATHER_API_KEY")


# https://github.com/juhilsomaiya/API-Integrations-Python/blob/master/Weather_forecast/main.p
@router.post('/api/temperature')
async def current_weather(city:City):
    """Retrieve current weather data from openweathermap

    Fetch weather data from openweathermap
    - description
    - temperature
    - high and low
    - humidity
    - wind speed
    - real feel forecast
    - pressure

    args:
        city: The target city

    returns:
        Dictionary that contains the requested data, which is converted
        by fastAPI to a json object.

    """
    app_id = weather_api
    location = validate_city(city) # {city: "New York", state: "NY" }
    city_name = location.city + "," + location.state
    county_code = "US"
    api_call = 'http://api.openweathermap.org/data/2.5/weather?q=' + city_name + ',' + county_code + '&appid=' + app_id + '&mode=json&units=imperial'
    data = requests.get(api_call)

    data = data.json()
    main = data['main']
    today = datetime.datetime.today()
    return {
        "Date": today.strftime("%m/%d/%y"),
        "Description": data['weather'][0]['description'],
        "Temperature": str(main['temp'])+" F\N{DEGREE SIGN}",
        "High Today": str(main['temp_max'])+" F\N{DEGREE SIGN}",
        "Low Today": str(main['temp_min'])+" F\N{DEGREE SIGN}",
        "Humidity": str(main['humidity'])+ "%",
        "Wind Speed": str(data['wind']['speed'])+ " mph",
        "Feels Like": str(main['feels_like'])+" F\N{DEGREE SIGN}",
        "Pressure": str(main['pressure'])+" hPa"
    }

##############################################################################################

#https://www.youtube.com/watch?v=eN_3d4JrL_w
@router.post('/api/job_opportunities')
async def job_opportunities(position, city:City):
    """Returns jobs opportunities from indeed.com

    Fetch first 10 job opportunities
    - Job title,
    - Company,
    - Job location
    - Post Date,
    - Extract Date,
    - Job Description,
    - Salary,
    - Job Url

    args:
        - position: desired job opportunity
        - city: target city

    returns:
        Dictionary that contains the requested data, which is converted
        by fastAPI to a json object.

    """
    # Run the main program reouting
    records = []  # creating the record list

    city_name = validate_city(city)
    location = city_name.city + ' ' + city_name.state
    url = get_url(position, location)  # create the url while passing in the position and location.

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    cards = soup.find_all('div', 'jobsearch-SerpJobCard')

    for card in cards:
        record = get_record(card)
        records.append(record)

    #also return total number of jobs
    try:
        total_jobs = soup.find('div', id='searchCountPages').text.strip()
        total = total_jobs.split()[-2:]
        jobs = ' '.join(total)
    except AttributeError:
        total_jobs = ''
        jobs = ''

    return {"Search Results":jobs, "Top 10 Listings": records}

def get_record(card):
    """Extract job date from a single record"""
    atag = card.h2.a
    job_title = atag.get('title')
    company = card.find('span', 'company').text.strip()
    job_location = card.find('div', 'recJobLoc').get('data-rc-loc')
    job_summary = card.find('div', 'summary').text.strip()
    post_date = card.find('span', 'date').text.strip()

    try:
        salary = card.find('span', 'salarytext').text.strip()
    except AttributeError:
        salary = ''

    extract_date = datetime.datetime.today().strftime('%Y-%m-%d')
    job_url = 'https://www.indeed.com' + atag.get('href')

    record = {'Job Title': job_title,
              'Company': company,
              'Location': job_location,
              'Date Posted': post_date,
              'Extract Date': extract_date,
              'Description': job_summary,
              'Salary': salary,
              'Job Url': job_url}

    return record


def get_url(position, location):
    "Generate a url based on position and location"

    template = "https://www.indeed.com/jobs?q={}&l={}"
    url = template.format(position, location)
    return url


def generate_climate_url(city, state) -> str:
    """Cleans input if necessary and formats the url to pass it to get_forecast().

    Args:
        city (str): Name of the city
        state (str): Name of the state

    Returns:
        str: Returns url for the desired location.
    """

    cleaned_input = []
    for string in [city, state]:
        string = string.lower().strip()

        if ' ' in string:
            input_str_list = list(string)
            for index, value in enumerate(input_str_list):
                if value == ' ':
                    input_str_list[index] = '-'

            string = "".join(input_str_list)

        cleaned_input.append(string)

    return (f'https://www.usclimatedata.com/climate/'
            f'{cleaned_input[0]}/{cleaned_input[1]}/united-states/')


@router.post('/api/climate')
async def get_forecast(city: City, function_=generate_climate_url):
    """Scrapes climate data from usclimatedata.com and returns the average
       highs and lows of each month.

    Args:
        city (City): Object from City class in /ml.py.
        function_ (generate_climate_url()): Generates the climate scraper url.

    Returns:
        dict: Dictionary that contains the average highs and lows for
        each month of the year.
    """

    city_name = validate_city(city)

    response = requests.get(
        generate_climate_url(city_name.city, city_name.state))
    soup = BeautifulSoup(response.content, 'html.parser')

    avg_high_monthly = []
    high_temp = soup.find_all('td', 'high text-right')

    for temp in high_temp[:12]:
        avg_high_monthly.append(int(temp.text.strip()))

    avg_low_monthly = []
    low_temp = soup.find_all('td', 'low text-right')

    for temp in low_temp[:12]:
        avg_low_monthly.append(int(temp.text.strip()))

    data_dict = {}
    data_dict['avg_high'] = avg_high_monthly
    data_dict['avg_low'] = avg_low_monthly

    return data_dict


class Settings(BaseSettings):

    RENTAL_API_KEY: SecretStr

    class Config:
        env_file = ".env"

settings = Settings()

headers={'x-rapidapi-key': os.getenv("RENTAL_API_KEY"),
            'x-rapidapi-host':  "realtor-com-real-estate.p.rapidapi.com"}

@router.post('/api/rental_listing')
async def rental_listing(
            city:City,
            api_key=settings.RENTAL_API_KEY,
            beds_min: int=1,
            baths_min: int=1,
            prop_type: str="apartment",
            limit: int=5):

    """
    args:
    - api_key
    - city: str
    - state: str Two-letter abbreviation
    - beds_min: int number of minimum bedrooms
    - baths_min: int number of minimum bathrooms
    - prop_type: str ('condo', 'single_family', 'apartment', 'multi_family')
    - limit: int number of results to populate


    returns:
        Dictionary that contains the requested data, which is converted
        by fastAPI to a json object.
    """

    city = validate_city(city)
    location_city = city.city
    location_state = city.state

    url="https://realtor-com-real-estate.p.rapidapi.com/for-rent"

    querystring={
                "city": location_city,
                "state_code": location_state,
                "limit": limit,
                "offset": "0",
                "beds_min": beds_min,
                "baths_min": baths_min,
                "sort": "relevance",
                "prop_type": prop_type}

    response_for_rent=requests.request("GET", url, params=querystring, headers=headers)
    response = response_for_rent.json()['data']['results']

    rental_list=[]

    for i in range(limit):
        lat = response[i]['location']['address']['coordinate']['lat']
        lon  = response[i]['location']['address']['coordinate']['lon']
        line = response[i]['location']['address']['line']
        city = response[i]['location']['address']['city']
        state = response[i]['location']['address']['state']
        pet_policy = response[i]['pet_policy']
        try:
            baths = response[i]['description']['baths_max']
        except AttributeError:
            baths = 0
        try:
            bedrooms = response[i]['description']['beds_max']
        except AttributeError:
            bedrooms = 0
        if pet_policy != None:
            cats_allowed = response[i]['pet_policy']['cats']
        else:
            cats_allowed = 'Unknown'
        if pet_policy != None:
            dogs_allowed = response[i]['pet_policy']['dogs']
        else:
            dogs_allowed = 'Unknown'
        list_price = response[i]['list_price_max']
        try:
            ammenities = response[i]['tags']
        except AttributeError:
            ammenities = []
        try:
            photos = response[i]['photos']
        except AttributeError:
            photos = None

        elements={
            'Latitude': lat,
            'Longitude': lon,
            'Street Address': line,
            'City': city,
            'State': state,
            'Bedrooms': bedrooms,
            'Bathrooms': baths,
            'Cats Allowed': cats_allowed,
            'Dogs Allowed': dogs_allowed,
            'List Price': list_price,
            'Ammenities': ammenities,
            'Photos': photos,
      }
        rental_list.append(elements)

    return rental_list

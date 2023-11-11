import os
import re
import pandas as pd
import requests
import logging
import datetime

from dotenv import load_dotenv

BASE_URL = 'https://api.themoviedb.org/3/'

# Basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_movie_titles(directory_path, excluded_folders=[]):
    movie_titles = []

    for root, dirs, files in os.walk(directory_path):
        # Normalize paths before comparison
        root_normalized = os.path.normpath(root)
        excluded_folders_normalized = [os.path.normpath(excluded) for excluded in excluded_folders]

        if any(os.path.commonpath([root_normalized, excluded]) == excluded for excluded in excluded_folders_normalized):
            continue
        # rest of the code...

        for file in files:
            if file.endswith(('.avi', '.mkv', '.mp4')) and not file.startswith('.'):
                title_without_extension = os.path.splitext(file)[0]
                movie_titles.append(title_without_extension)

    return movie_titles


# def extract_series_titles(root_path, excluded_folders=[]):
#     series_titles = []
#
#     for root, dirs, _ in os.walk(root_path):
#         # Skip excluded folders
#         if os.path.basename(root) in excluded_folders:
#             continue
#
#         for dir_name in dirs:
#             series_titles.append(dir_name)
#
#     logging.info("Series list correctly pulled")
#     return series_titles


def clean_title(title):
    # A series of regular expressions to clean up the title
    patterns = [
        r'\[.*?\]',  # Remove anything in square brackets
        r'\(.*?\)',  # Remove anything in round brackets
        r'1080p|720p|480p',  # Remove common resolutions
        r'BluRay|DVD|HDRip|HD',  # Remove release types
        r'film completo',  # Specific phrases
        r'Full Movie by Film&Clips',
        r'by .*$',  # 'by' and everything that follows
        r'Versione Restaurata',
        r'Subtitle',
        r'Film',
        r'Full',
        r'Pelicula Completa',
        r'IN ITALIANO',
        r'Movie',
        r'(?<![a-zA-Z])-(?![a-zA-Z])',  # Remove dashes not between words
        # r'\d{4}.*$',  # Remove any four digits (like 1985) and everything that follows
    ]

    for pattern in patterns:
        # re.IGNORECASE makes the regex pattern case-insensitive
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    # Replacing underscores with space
    title = title.replace('_', ' ')

    title = title.strip()  # Remove any leading/trailing whitespace
    return title


def append_no_result_data(data_dict, title):
    """
    Helper function to append "no result" data to the movies_data dictionary.
    """
    data_dict['title'].append(title)
    data_dict['release_year'].append('')
    data_dict.setdefault('director', []).append('')
    data_dict['genre'].append('')
    data_dict.setdefault('duration_minutes', []).append('')
    data_dict['country_of_production'].append('')
    data_dict['language'].append('')
    data_dict['main_actors'].append('')
    data_dict['rating'].append('')
    data_dict['synopsis'].append('')
    data_dict['Seen'].append('')  # Placeholder for manual input
    data_dict['Subtitles'].append('')  # Placeholder for manual input


def get_movie_details(titles):
    logging.info("Retrieving movies from TMDB")
    load_dotenv()
    tmdb_api_key = os.getenv('TMDB_API_KEY')

    # Assuming BASE_URL is defined elsewhere
    # BASE_URL = "https://api.themoviedb.org/3/"

    movies_data = {
        'file_title': [],
        'title': [],
        'release_year': [],
        'director': [],
        'genre': [],
        'duration_minutes': [],
        'country_of_production': [],
        'language': [],
        'main_actors': [],
        'rating': [],
        'synopsis': [],
        'Seen': [],
        'Subtitles': []
    }

    for title in titles:
        movies_data['file_title'].append(title)

        year_match = re.search(r'(\d{4})', title)
        year = year_match.group(1) if year_match else ''
        current_year = datetime.datetime.now().year
        if year:  # Check if the year string is not empty
            try:
                # Attempt to convert year string to an integer and then check if it falls within the valid range
                if not (1880 <= int(year) <= current_year):
                    year = ''
            except ValueError:
                year = ''

        # Clean the title
        cleaned_title = title.replace(year, '').strip()
        if title.isdigit() and not year:
            cleaned_title = title

        # If a year is found, add it to the search URL
        if year:
            search_url = f"{BASE_URL}search/movie?api_key={tmdb_api_key}&query={cleaned_title}&year={year}"
        else:
            search_url = f"{BASE_URL}search/movie?api_key={tmdb_api_key}&query={cleaned_title}"

        # search_url = f"{BASE_URL}search/movie?api_key={tmdb_api_key}&query={cleaned_title}"
        response = requests.get(search_url).json()

        # Try to extract movie ID
        movie_id = None
        if response['results']:
            if year:
                filtered_results = [result for result in response['results'] if year in result['release_date']]
                if filtered_results:
                    movie_id = filtered_results[0]['id']
            else:
                movie_id = response['results'][0]['id']

        # Fetch and store movie details
        if movie_id:
            movie_url = f"{BASE_URL}movie/{movie_id}?api_key={tmdb_api_key}"
            movie_data = requests.get(movie_url).json()

            credits_url = f"{BASE_URL}movie/{movie_id}/credits?api_key={tmdb_api_key}"
            credits_data = requests.get(credits_url).json()

            director = next((member['name'] for member in credits_data['crew'] if member['job'] == 'Director'), None)

            movies_data['title'].append(movie_data.get('original_title', 'N/A'))
            movies_data['release_year'].append(movie_data.get('release_date', 'N/A').split('-')[0])
            movies_data['director'].append(director if director else 'N/A')
            movies_data['genre'].append(
                ', '.join([g['name'] for g in movie_data['genres']]) if movie_data.get('genres') else 'N/A')
            movies_data['duration_minutes'].append(movie_data.get('runtime', 'N/A'))
            movies_data['country_of_production'].append(
                movie_data['production_countries'][0]['name'] if movie_data.get('production_countries') else 'N/A')
            movies_data['language'].append(movie_data.get('original_language', 'N/A'))
            movies_data['main_actors'].append(
                ', '.join([c['name'] for c in credits_data['cast'][:3]]) if credits_data.get('cast') else 'N/A')
            movies_data['rating'].append(movie_data.get('vote_average', 'N/A'))
            movies_data['synopsis'].append(movie_data.get('overview', 'N/A'))
            movies_data['Seen'].append('')
            movies_data['Subtitles'].append('')
        else:
            append_no_result_data(movies_data, title)

    logging.info("All movies retrieved")
    return movies_data


def get_series_details(titles):
    # Initialize an empty dictionary to hold the details of all series
    series_data = {
        'file_title': [],
        'title': [],
        'release_year': [],
        'creator': [],
        'genre': [],
        'seasons_count': [],
        'country_of_production': [],
        'language': [],
        'main_actors': [],
        'rating': [],
        'synopsis': [],
        'Seen': [],
        'Subtitles': []
    }

    logging.info("Retrieving series from TMDB")
    load_dotenv()

    # Get the API key
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')

    for title in titles:
        # ... [Kept the same until the extraction of the year]

        # Attempt to extract the year from the title
        year_match = re.search(r'(\d{4})', title)
        year = year_match.group(1) if year_match else ''

        # Validate the year
        current_year = datetime.datetime.now().year
        try:
            # Check if the extracted year is a valid year
            if not (1880 <= int(year) <= current_year):
                year = ''
        except ValueError:
            year = ''  # Set year to empty string if it can't be converted to an integer

        cleaned_title = title.replace(year, '').strip()

        search_url = f"{BASE_URL}search/tv?api_key={TMDB_API_KEY}&query={cleaned_title}"
        response = requests.get(search_url).json()

        # If we find results
        if response['results']:
            series_id = response['results'][0]['id']

            # Fetching general series details
            series_url = f"{BASE_URL}tv/{series_id}?api_key={TMDB_API_KEY}"
            series_data_response = requests.get(series_url).json()

            # Adding details to the series_data dictionary
            series_data['title'].append(series_data_response.get('original_name', 'N/A'))
            series_data['release_year'].append(series_data_response.get('first_air_date', 'N/A').split('-')[0])
            series_data['creator'].append(series_data_response.get('created_by', [{'name': 'N/A'}])[0]['name'])
            series_data['genre'].append(', '.join([g['name'] for g in series_data_response['genres']]))
            series_data['seasons_count'].append(len(series_data_response.get('seasons', [])))
            series_data['country_of_production'].append(series_data_response.get('origin_country', ['N/A'])[0])
            series_data['language'].append(series_data_response.get('original_language', 'N/A'))
            cast = series_data_response.get('cast', [])
            if cast:
                series_data['main_actors'].append(', '.join([c['name'] for c in cast[:3]]))
            else:
                series_data['main_actors'].append('N/A')
            series_data['rating'].append(series_data_response.get('vote_average', 'N/A'))
            series_data['synopsis'].append(series_data_response.get('overview', 'N/A'))
            series_data['Seen'].append('')  # Placeholder for manual input
            series_data['Subtitles'].append('')  # Placeholder for manual input

        else:  # If no results are found at all
            append_no_result_data(series_data, title)
    logging.info("All series retrieved")

    return series_data


def save_to_csv(movies_data, csv_path):
    """
    Saves the movies data to a CSV file. If the CSV file already exists,
    it appends the new data without adding duplicates based on the 'title' column.
    """
    # If the CSV file exists, read it
    logging.info("Now saving .csv file")
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
    else:
        existing_df = pd.DataFrame()

    # Convert the movies_data dict to a DataFrame
    new_df = pd.DataFrame(movies_data)

    # Append the new data to the existing data without adding duplicates
    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['title', 'release_year']).reset_index(
        drop=True)

    # Save the combined data back to the CSV file
    combined_df.to_csv(csv_path, index=False)

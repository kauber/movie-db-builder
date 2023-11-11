import argparse
# import csv
from utils import (extract_movie_titles, clean_title,
                   get_movie_details, get_series_details, save_to_csv)


# TODO: solve for the series
# TODO: find a way to connect to postgres database, upload or update tables
# TODO: when movie added to hd, automatically add them to postgres, only new ones


def main(directory_path, excluded_folders=[]):
    # Movies

    movie_list = extract_movie_titles(directory_path, excluded_folders)
    movie_list = [clean_title(movie) for movie in movie_list]
    movies = get_movie_details(movie_list)
    save_to_csv(movies, "movies_db.csv")

    # python main.py D:/Films --excluded-folder D:/Films/Serie-Sceneggiati D:/Films/TrasmissioniTV


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract movie details and save to CSV.')
    # Required directory argument
    parser.add_argument('directory', type=str, help='The directory path to search for movie titles.')
    # Optional excluded folder argument
    parser.add_argument('--excluded-folders', type=str, nargs='*', default=[], help='The directories to exclude from '
                                                                                    'search, separated by space.')
    args = parser.parse_args()
    main(args.directory, args.excluded_folders)

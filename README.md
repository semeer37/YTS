```
# YTS Movie Browser

A comprehensive toolkit for searching, browsing, and downloading movies from YTS.mx through both command-line and terminal user interfaces.

![YTS Movie Browser](https://img.shields.io/badge/YTS-Movie%20Browser-green)
![Python](https://img.shields.io/badge/Python-3.6+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
  - [Interactive CLI (cli.py)](#interactive-cli-clipy)
  - [Terminal UI (cli_tui.py)](#terminal-ui-cli_tuipy)
  - [API Client (api.py)](#api-client-apipy)
- [Development](#development)
- [License](#license)
- [Disclaimer](#disclaimer)

## Overview

YTS Movie Browser is a comprehensive toolkit that provides multiple ways to interact with the YTS.mx movie database:

1. **Interactive CLI** (`cli.py`): A command-line interface using InquirerPy for step-by-step interactive browsing
2. **Terminal UI** (`cli_tui.py`): A rich terminal user interface built with Textual for keyboard-driven navigation
3. **API Client Library** (`api.py`): A Python client for direct interaction with the YTS API

All components share the same underlying API client, ensuring consistent behavior and reducing code duplication.

## Features

### Common Features

- Search for movies by title
- Browse latest movie releases
- View detailed movie information
- Multiple download options:
  - Download .torrent files
  - Open magnet links in default torrent client
  - Download using aria2c
- Comprehensive error handling
- Configurable logging

### Interactive CLI Features

- Step-by-step guided workflow
- Rich terminal output with colors and formatting
- Command-line arguments for direct search and browse
- Verbose and quiet modes

### Terminal UI Features

- Full-screen terminal interface
- Keyboard navigation
- Data tables for movie listings
- Scrollable movie details
- Live download log panel

## Project Structure

```
yts-movie-browser/
├── api.py                 # YTS API client library
├── cli.py                 # Interactive CLI application
├── cli_tui.py             # Terminal UI application
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```

### Code Integration

Both CLI applications (`cli.py` and `cli_tui.py`) import the API client from `api.py`:

```python
# In cli.py and cli_tui.py
from api import YTSClient, YTSAPIError, YTSRequestError, YTSResponseError, YTSParameterError
```

This modular approach ensures:
- Consistent API interaction across applications
- Easier maintenance (changes to API handling only need to be made in one place)
- Reduced code duplication
- Better separation of concerns

## Installation

### Requirements

- Python 3.6+
- Required packages:
  - click
  - rich
  - InquirerPy
  - textual
  - pathlib
  - requests

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/yts-movie-browser.git
   cd yts-movie-browser
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Make the scripts executable:
   ```bash
   chmod +x api.py cli.py cli_tui.py
   ```

## Usage

### Interactive CLI (`cli.py`)

The interactive CLI provides a step-by-step interface for searching and downloading movies.

#### Basic Usage

```bash
# Launch the interactive menu
python cli.py

# Search for movies directly
python cli.py search "movie name"

# Browse latest movies
python cli.py browse

# Enable verbose logging
python cli.py --verbose

# Suppress all output except errors
python cli.py --quiet
```

#### Interactive Flow

1. **Main Menu**: Choose between searching for movies or browsing latest releases
   ```
   What would you like to do?
   > Search for movies
     Browse latest movies
     Exit
   ```

2. **Search**: Enter a movie name to search
   ```
   Enter movie name to search (or leave empty to go back): Batman
   ```

3. **Select Movie**: Choose from search results
   ```
   Select a movie:
   > The Batman (2022) - Rating: 7.8/10
     Batman Begins (2005) - Rating: 8.2/10
     The Dark Knight (2008) - Rating: 9.0/10
     ← Back
     Exit
   ```

4. **View Details**: See movie information and available downloads
   ```
   The Batman (2022)
   
   Rating: 7.8/10
   Runtime: 176 minutes
   Genres: Action, Crime, Drama
   
   Description:
   When the Riddler, a sadistic serial killer, begins murdering key political figures in Gotham, Batman is forced to investigate the city's hidden corruption and question his family's involvement.
   
   Available Downloads:
   Quality  Type  Size      Seeds  Peers
   720p     web   1.02 GB   15     6
   1080p    web   2.09 GB   19     6
   2160p    web   5.07 GB   2      3
   ```

5. **Select Quality**: Choose download quality
   ```
   Select a quality:
   > 1080p (web) - Size: 2.09 GB - Seeds: 19
     720p (web) - Size: 1.02 GB - Seeds: 15
     2160p (web) - Size: 5.07 GB - Seeds: 2
     ← Back
     Exit
   ```

6. **Download Options**: Choose download method
   ```
   Select download method:
   > Download .torrent file
     Open magnet link in default torrent app
     Download using aria2c
     ← Back
     Exit
   ```

### Terminal UI (`cli_tui.py`)

The Terminal UI app provides a rich, interactive interface with keyboard navigation.

#### Basic Usage

```bash
# Launch the TUI app
python cli_tui.py

# Enable verbose logging
python cli_tui.py --verbose

# Suppress all output except errors
python cli_tui.py --quiet
```

#### Keyboard Navigation

- **Arrow keys**: Navigate through lists and options
- **Enter**: Select an item
- **Escape**: Go back to previous screen
- **q**: Quit the application
- **s**: Go to search screen
- **b**: Browse latest movies
- **d**: Show download options (when viewing movie details)

#### Screens

1. **Home Screen**: Main entry point with options to search or browse
2. **Search Screen**: Enter a movie name to search
3. **Results Screen**: View and select from search results or browse results
4. **Movie Details Screen**: View movie information and available downloads
5. **Download Screen**: Choose download method and view download log

### API Client (`api.py`)

The API client can be used independently in your own Python projects:

```python
from api import YTSClient, YTSAPIError

# Initialize the client
client = YTSClient()

try:
    # Search for movies
    movies = client.search_movies("Batman")
    print(f"Found {movies.get('movie_count', 0)} movies")
    
    # Get movie details
    movie = client.movie_details(movie_id=10)
    print(f"Title: {movie.get('movie', {}).get('title')}")
    
    # Get movie suggestions
    suggestions = client.movie_suggestions(movie_id=10)
    
    # Get parental guides
    guides = client.movie_parental_guides(movie_id=10)
    
    # Construct a magnet URL
    hash_value = "ABCDEF1234567890"
    movie_title = "Example Movie"
    magnet_url = client.construct_magnet_url(hash_value, movie_title)
    
    # Download a torrent file
    client.download_torrent_file("https://example.com/movie.torrent", "/path/to/save/movie.torrent")
    
except YTSAPIError as e:
    print(f"Error: {e}")
```

#### Available Methods

- `list_movies()`: Search and filter movies with various parameters
- `search_movies()`: Search for movies by name (simplified wrapper around list_movies)
- `list_latest_movies()`: Get latest movies (simplified wrapper around list_movies)
- `movie_details()`: Get detailed information about a specific movie
- `movie_suggestions()`: Get movie suggestions related to a specific movie
- `movie_parental_guides()`: Get parental guide information for a specific movie
- `construct_magnet_url()`: Create a magnet URL from a torrent hash and title
- `download_torrent_file()`: Download a torrent file from a URL

## Additional Information

### Logging

Both CLI applications log operations to files:
- `yts_cli.log`: Logs from the interactive CLI
- `yts_tui.log`: Logs from the Terminal UI app

Log levels can be controlled with the `--verbose` and `--quiet` flags.

### Downloads

Downloaded files are saved to `~/Downloads/YTS_Downloads/` by default.


## Disclaimer

This tool is for educational purposes only. Please respect copyright laws and only download content that you have the legal right to access.
```

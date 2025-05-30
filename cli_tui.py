#!/usr/bin/env python3
"""
YTS API Terminal UI Application

This TUI tool allows users to search, browse, and download movie torrents from YTS.
It provides a rich terminal user interface using Textual for interactive navigation.

Usage:
    python cli_tui.py
"""

import os
import sys
import time
import logging
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, Input, Label, ListItem, ListView,
    LoadingIndicator, Log, Static, DataTable, Placeholder
)
from textual.reactive import reactive
from textual import events, work

# Import YTS API client from api.py
from api import YTSClient, YTSAPIError, YTSRequestError, YTSResponseError, YTSParameterError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, markup=True),
        logging.FileHandler("yts_tui.log")
    ]
)
logger = logging.getLogger("yts_tui")

# Initialize rich console
console = Console()

# Constants
DOWNLOAD_DIR = Path.home() / "Downloads" / "YTS_Downloads"


class DownloadManager:
    """Manager for handling downloads."""
    
    @staticmethod
    def download_torrent_file(url: str, movie_title: str, quality: str, log_callback: Callable = None) -> Optional[Path]:
        """Download a torrent file from the given URL."""
        # Create download directory if it doesn't exist
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        safe_title = "".join(c if c.isalnum() or c in " ._-" else "_" for c in movie_title)
        filename = f"{safe_title}_{quality}.torrent"
        file_path = DOWNLOAD_DIR / filename
        
        try:
            if log_callback:
                log_callback(f"Downloading {filename}...")
            
            # Use the API client to download the torrent file
            client = YTSClient()
            client.download_torrent_file(url, str(file_path))
            
            if log_callback:
                log_callback(f"Success: Torrent file downloaded to {file_path}")
            
            return file_path
        
        except YTSAPIError as e:
            logger.error(f"Failed to download torrent file: {str(e)}")
            if log_callback:
                log_callback(f"Error: Failed to download torrent file. {str(e)}")
            return None
    
    @staticmethod
    def open_magnet_link(magnet_url: str, log_callback: Callable = None) -> bool:
        """Open the magnet link in the default torrent application."""
        try:
            if log_callback:
                log_callback("Opening magnet link in your default torrent application...")
            
            webbrowser.open(magnet_url)
            
            if log_callback:
                log_callback("Magnet link opened successfully.")
            
            return True
        except Exception as e:
            logger.error(f"Failed to open magnet link: {str(e)}")
            if log_callback:
                log_callback(f"Error: Failed to open magnet link. {str(e)}")
            return False
    
    @staticmethod
    def download_with_aria2c(magnet_url: str, log_callback: Callable = None) -> bool:
        """Download using aria2c command-line tool."""
        try:
            # Check if aria2c is installed
            try:
                subprocess.run(["aria2c", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                if log_callback:
                    log_callback("Error: aria2c is not installed. Please install it first.")
                return False
            
            # Create download directory if it doesn't exist
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            
            # Start download
            if log_callback:
                log_callback("Starting download with aria2c...")
            
            process = subprocess.Popen(
                ["aria2c", "--dir", str(DOWNLOAD_DIR), magnet_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if log_callback:
                log_callback(f"Download started! Files will be saved to {DOWNLOAD_DIR}")
                log_callback("Download is running in the background. Check aria2c output for progress.")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to start aria2c download: {str(e)}")
            if log_callback:
                log_callback(f"Error: Failed to start download with aria2c. {str(e)}")
            return False


class SearchScreen(Screen):
    """Screen for searching movies."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the search screen."""
        yield Header(show_clock=True)
        yield Container(
            Label("Search Movies", classes="title"),
            Input(placeholder="Enter movie name to search...", id="search_input"),
            Button("Search", variant="primary", id="search_button"),
            Button("Browse Latest", variant="default", id="browse_button"),
            id="search_container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "search_button":
            query = self.query_one("#search_input").value
            if query:
                self.app.push_screen(
                    LoadingScreen(next_screen="results", query=query),
                    {"query": query}
                )
        elif event.button.id == "browse_button":
            self.app.push_screen(
                LoadingScreen(next_screen="results", query=None),
                {"query": None}
            )
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission events."""
        if event.input.id == "search_input":
            query = event.input.value
            if query:
                self.app.push_screen(
                    LoadingScreen(next_screen="results", query=query),
                    {"query": query}
                )


class LoadingScreen(Screen):
    """Screen displayed while loading data."""
    
    def __init__(self, next_screen: str, query: Optional[str] = None):
        """Initialize the loading screen."""
        super().__init__()
        self.next_screen = next_screen
        self.query = query
    
    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        yield Container(
            LoadingIndicator(),
            Label("Loading data from YTS API...", id="loading_label"),
            id="loading_container",
        )
    
    def on_mount(self) -> None:
        """Handle the mount event."""
        self.load_data()
    
    @work(thread=True)
    def load_data(self) -> None:
        """Load data from the API."""
        client = YTSClient()
        
        try:
            if self.next_screen == "results":
                if self.query:
                    # Use the search_movies method from the API client
                    response = client.search_movies(self.query)
                    title = f"Search Results for '{self.query}'"
                else:
                    # Use the list_latest_movies method from the API client
                    response = client.list_latest_movies()
                    title = "Latest Movies"
                
                # Extract movie data
                movies = response.get("movies", [])
                
                self.app.call_from_thread(
                    self.app.push_screen,
                    ResultsScreen(movies=movies, title=title)
                )
            elif self.next_screen == "details":
                movie_id = int(self.query)
                # Use the movie_details method from the API client
                response = client.movie_details(movie_id=movie_id)
                
                # Extract movie data
                movie = response.get("movie", {})
                
                self.app.call_from_thread(
                    self.app.push_screen,
                    MovieDetailsScreen(movie=movie)
                )
        except YTSAPIError as e:
            logger.error(f"API error: {str(e)}")
            self.app.call_from_thread(
                self.app.push_screen,
                ErrorScreen(message=f"API Error: {str(e)}")
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self.app.call_from_thread(
                self.app.push_screen,
                ErrorScreen(message=f"Unexpected Error: {str(e)}")
            )


class ResultsScreen(Screen):
    """Screen for displaying movie search results."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]
    
    def __init__(self, movies: List[Dict[str, Any]], title: str):
        """Initialize the results screen."""
        super().__init__()
        self.movies = movies
        self.screen_title = title
    
    def compose(self) -> ComposeResult:
        """Compose the results screen."""
        yield Header(show_clock=True)
        
        if not self.movies:
            yield Container(
                Label("No movies found", classes="error"),
                id="results_container",
            )
        else:
            movie_table = DataTable(id="movie_table")
            movie_table.add_columns("ID", "Title", "Year", "Rating", "Genres")
            
            for movie in self.movies:
                movie_id = movie.get("id", "N/A")
                title = movie.get("title", "Unknown Title")
                year = str(movie.get("year", "N/A"))
                rating = str(movie.get("rating", "N/A"))
                genres = ", ".join(movie.get("genres", [])[:2])  # Show only first 2 genres
                
                movie_table.add_row(str(movie_id), title, year, rating, genres)
            
            yield Container(
                Label(self.screen_title, classes="title"),
                movie_table,
                id="results_container",
            )
        
        yield Footer()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection events."""
        row_index = event.row_key.row
        if 0 <= row_index < len(self.movies):
            selected_movie = self.movies[row_index]
            self.app.push_screen(
                LoadingScreen(next_screen="details", query=str(selected_movie.get("id"))),
                {"movie_id": selected_movie.get("id")}
            )


class MovieDetailsScreen(Screen):
    """Screen for displaying movie details."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
        Binding("d", "show_download_options", "Download"),
    ]
    
    def __init__(self, movie: Dict[str, Any]):
        """Initialize the movie details screen."""
        super().__init__()
        self.movie = movie
    
    def compose(self) -> ComposeResult:
        """Compose the movie details screen."""
        yield Header(show_clock=True)
        
        title = self.movie.get("title", "Unknown Title")
        year = self.movie.get("year", "Unknown Year")
        rating = self.movie.get("rating", "N/A")
        runtime = self.movie.get("runtime", "N/A")
        genres = ", ".join(self.movie.get("genres", []))
        description = self.movie.get("description_full", "No description available.")
        
        # Movie details
        yield ScrollableContainer(
            Label(f"{title} ({year})", classes="title"),
            Static(f"Rating: {rating}/10 | Runtime: {runtime} min | Genres: {genres}"),
            Static(""),
            Static("Description:"),
            Static(description),
            Static(""),
            Label("Available Downloads:", classes="subtitle"),
            id="details_container",
        )
        
        # Torrent options
        torrents = self.movie.get("torrents", [])
        if torrents:
            torrent_table = DataTable(id="torrent_table")
            torrent_table.add_columns("Quality", "Type", "Size", "Seeds", "Peers")
            
            for torrent in torrents:
                quality = torrent.get("quality", "Unknown")
                type_info = torrent.get("type", "Unknown")
                size = torrent.get("size", "Unknown")
                seeds = str(torrent.get("seeds", "0"))
                peers = str(torrent.get("peers", "0"))
                
                torrent_table.add_row(quality, type_info, size, seeds, peers)
            
            yield Container(
                torrent_table,
                id="torrents_container",
            )
        else:
            yield Container(
                Label("No torrents available for this movie", classes="error"),
                id="torrents_container",
            )
        
        yield Footer()
    
    def action_show_download_options(self) -> None:
        """Show download options for the selected torrent."""
        torrent_table = self.query_one("#torrent_table", DataTable)
        if torrent_table.cursor_row is not None:
            row_index = torrent_table.cursor_row
            torrents = self.movie.get("torrents", [])
            
            if 0 <= row_index < len(torrents):
                selected_torrent = torrents[row_index]
                self.app.push_screen(
                    DownloadScreen(
                        torrent=selected_torrent,
                        movie_title=self.movie.get("title", "Unknown")
                    )
                )


class DownloadScreen(Screen):
    """Screen for downloading torrents."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]
    
    def __init__(self, torrent: Dict[str, Any], movie_title: str):
        """Initialize the download screen."""
        super().__init__()
        self.torrent = torrent
        self.movie_title = movie_title
        self.client = YTSClient()
        self.download_manager = DownloadManager()
    
    def compose(self) -> ComposeResult:
        """Compose the download screen."""
        yield Header(show_clock=True)
        
        quality = self.torrent.get("quality", "Unknown")
        size = self.torrent.get("size", "Unknown")
        
        yield Container(
            Label(f"Download Options for {self.movie_title} ({quality})", classes="title"),
            Static(f"Size: {size}"),
            Static(""),
            Button("Download .torrent file", variant="primary", id="torrent_button"),
            Button("Open magnet link", variant="success", id="magnet_button"),
            Button("Download with aria2c", variant="warning", id="aria2c_button"),
            id="download_container",
        )
        
        yield Container(
            Label("Download Log", classes="subtitle"),
            Log(id="download_log", highlight=True, markup=True),
            id="log_container",
        )
        
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        log = self.query_one("#download_log", Log)
        
        if event.button.id == "torrent_button":
            self.download_torrent_file(log)
        elif event.button.id == "magnet_button":
            self.open_magnet_link(log)
        elif event.button.id == "aria2c_button":
            self.download_with_aria2c(log)
    
    @work(thread=True)
    def download_torrent_file(self, log: Log) -> None:
        """Download the torrent file."""
        url = self.torrent.get("url", "")
        quality = self.torrent.get("quality", "Unknown")
        
        def log_callback(message: str) -> None:
            self.app.call_from_thread(log.write, message)
        
        self.download_manager.download_torrent_file(url, self.movie_title, quality, log_callback)
    
    @work(thread=True)
    def open_magnet_link(self, log: Log) -> None:
        """Open the magnet link."""
        hash_value = self.torrent.get("hash", "")
        # Use the API client to construct the magnet URL
        magnet_url = self.client.construct_magnet_url(hash_value, self.movie_title)
        
        def log_callback(message: str) -> None:
            self.app.call_from_thread(log.write, message)
        
        self.download_manager.open_magnet_link(magnet_url, log_callback)
    
    @work(thread=True)
    def download_with_aria2c(self, log: Log) -> None:
        """Download using aria2c."""
        hash_value = self.torrent.get("hash", "")
        # Use the API client to construct the magnet URL
        magnet_url = self.client.construct_magnet_url(hash_value, self.movie_title)
        
        def log_callback(message: str) -> None:
            self.app.call_from_thread(log.write, message)
        
        self.download_manager.download_with_aria2c(magnet_url, log_callback)


class ErrorScreen(Screen):
    """Screen for displaying errors."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]
    
    def __init__(self, message: str):
        """Initialize the error screen."""
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        """Compose the error screen."""
        yield Header(show_clock=True)
        yield Container(
            Label("Error", classes="title error"),
            Static(self.message),
            Button("Back", variant="primary", id="back_button"),
            id="error_container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "back_button":
            self.app.pop_screen()


class YTSApp(App):
    """Main YTS TUI application."""
    
    TITLE = "YTS Movie Browser"
    CSS = """
    Screen {
        background: $surface;
    }
    
    .title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin: 1 0;
        width: 100%;
    }
    
    .subtitle {
        text-style: bold;
        color: $text;
        margin: 1 0;
    }
    
    .error {
        color: $error;
    }
    
    #search_container {
        layout: vertical;
        content-align: center middle;
        padding: 2 4;
        width: 100%;
        height: 100%;
    }
    
    #search_container Input {
        width: 80%;
        margin: 1 0;
    }
    
    #search_container Button {
        margin: 1 0;
    }
    
    #loading_container {
        layout: vertical;
        content-align: center middle;
        padding: 2 4;
        width: 100%;
        height: 100%;
    }
    
    #results_container {
        layout: vertical;
        padding: 1 2;
        width: 100%;
        height: 100%;
    }
    
    #details_container {
        layout: vertical;
        padding: 1 2;
        width: 100%;
        height: 60%;
    }
    
    #torrents_container {
        layout: v

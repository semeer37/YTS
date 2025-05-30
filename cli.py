"""
YTS API Interactive CLI Application

This CLI tool allows users to search, browse, and download movie torrents from YTS.
It provides an interactive interface using InquirerPy for user interactions and rich for styled output.

Usage:
    python cli.py
    python cli.py search "movie name"
    python cli.py browse
"""

import os
import sys
import logging
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator

# Import YTS API client from api.py
from api import YTSClient, YTSAPIError, YTSRequestError, YTSResponseError, YTSParameterError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, markup=True),
        logging.FileHandler("yts_cli.log")
    ]
)
logger = logging.getLogger("yts_cli")

# Initialize rich console
console = Console()

# Constants
DOWNLOAD_DIR = Path.home() / "Downloads" / "YTS_Downloads"


def download_torrent_file(url: str, movie_title: str, quality: str) -> Optional[Path]:
    """Download a torrent file from the given URL."""
    # Create download directory if it doesn't exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_title = "".join(c if c.isalnum() or c in " ._-" else "_" for c in movie_title)
    filename = f"{safe_title}_{quality}.torrent"
    file_path = DOWNLOAD_DIR / filename
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]Downloading {filename}...[/]"),
            transient=False,
        ) as progress:
            task = progress.add_task("download", total=None)
            
            # Use the API client to download the torrent file
            client = YTSClient()
            client.download_torrent_file(url, str(file_path))
            
            progress.update(task, completed=1)
        
        console.print(f"[bold green]Success:[/] Torrent file downloaded to {file_path}")
        return file_path
    
    except YTSAPIError as e:
        logger.error(f"Failed to download torrent file: {str(e)}")
        console.print(f"[bold red]Error:[/] Failed to download torrent file. {str(e)}")
        return None


def open_magnet_link(magnet_url: str) -> bool:
    """Open the magnet link in the default torrent application."""
    try:
        console.print("[bold blue]Opening magnet link in your default torrent application...[/]")
        webbrowser.open(magnet_url)
        return True
    except Exception as e:
        logger.error(f"Failed to open magnet link: {str(e)}")
        console.print(f"[bold red]Error:[/] Failed to open magnet link. {str(e)}")
        return False


def download_with_aria2c(magnet_url: str) -> bool:
    """Download using aria2c command-line tool."""
    try:
        # Check if aria2c is installed
        try:
            subprocess.run(["aria2c", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            console.print("[bold red]Error:[/] aria2c is not installed. Please install it first.")
            return False
        
        # Create download directory if it doesn't exist
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Start download
        console.print("[bold blue]Starting download with aria2c...[/]")
        process = subprocess.Popen(
            ["aria2c", "--dir", str(DOWNLOAD_DIR), magnet_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        console.print(f"[bold green]Download started![/] Files will be saved to {DOWNLOAD_DIR}")
        console.print("[dim]Download is running in the background. Check aria2c output for progress.[/]")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start aria2c download: {str(e)}")
        console.print(f"[bold red]Error:[/] Failed to start download with aria2c. {str(e)}")
        return False


def display_movie_details(movie: Dict[str, Any]) -> None:
    """Display detailed information about a movie."""
    # Extract movie data
    title = movie.get("title", "Unknown Title")
    year = movie.get("year", "Unknown Year")
    rating = movie.get("rating", "N/A")
    runtime = movie.get("runtime", "N/A")
    genres = movie.get("genres", [])
    description = movie.get("description_full", "No description available.")
    
    # Create a rich table for movie details
    table = Table(title=f"{title} ({year})", show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    table.add_row("Rating", f"{rating}/10")
    table.add_row("Runtime", f"{runtime} minutes")
    table.add_row("Genres", ", ".join(genres))
    
    # Create a panel for the description
    description_panel = Panel(
        description,
        title="Description",
        border_style="blue",
        width=100
    )
    
    # Display movie details
    console.print("\n")
    console.print(table)
    console.print(description_panel)
    console.print("\n")


def display_torrent_options(torrents: List[Dict[str, Any]]) -> None:
    """Display available torrent options for a movie."""
    if not torrents:
        console.print("[yellow]No torrents available for this movie.[/]")
        return
    
    # Create a rich table for torrent options
    table = Table(title="Available Downloads", box=None)
    table.add_column("Quality", style="cyan")
    table.add_column("Type")
    table.add_column("Size")
    table.add_column("Seeds", style="green")
    table.add_column("Peers", style="yellow")
    
    for torrent in torrents:
        quality = torrent.get("quality", "Unknown")
        type_info = torrent.get("type", "Unknown")
        size = torrent.get("size", "Unknown")
        seeds = str(torrent.get("seeds", "0"))
        peers = str(torrent.get("peers", "0"))
        
        table.add_row(quality, type_info, size, seeds, peers)
    
    console.print(table)
    console.print("\n")


def select_movie_interactive(movies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to select a movie from a list."""
    if not movies:
        console.print("[yellow]No movies found.[/]")
        return None
    
    # Create choices for the inquirer prompt
    choices = []
    for movie in movies:
        title = movie.get("title", "Unknown Title")
        year = movie.get("year", "Unknown Year")
        rating = movie.get("rating", "N/A")
        
        # Create a choice with the movie as the value
        choices.append(Choice(
            value=movie,
            name=f"{title} ({year}) - Rating: {rating}/10"
        ))
    
    # Add back and exit options
    choices.append(Choice(value="back", name="← Back"))
    choices.append(Choice(value="exit", name="Exit"))
    
    # Prompt user to select a movie
    selected = inquirer.select(
        message="Select a movie:",
        choices=choices,
        default=choices[0] if choices else None,
    ).execute()
    
    if selected == "back":
        return "back"
    elif selected == "exit":
        console.print("[bold blue]Goodbye![/]")
        sys.exit(0)
    
    return selected


def select_torrent_interactive(torrents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to select a torrent from a list."""
    if not torrents:
        console.print("[yellow]No torrents available for this movie.[/]")
        return None
    
    # Create choices for the inquirer prompt
    choices = []
    for torrent in torrents:
        quality = torrent.get("quality", "Unknown")
        type_info = torrent.get("type", "Unknown")
        size = torrent.get("size", "Unknown")
        seeds = torrent.get("seeds", 0)
        
        # Create a choice with the torrent as the value
        choices.append(Choice(
            value=torrent,
            name=f"{quality} ({type_info}) - Size: {size} - Seeds: {seeds}"
        ))
    
    # Add back and exit options
    choices.append(Choice(value="back", name="← Back"))
    choices.append(Choice(value="exit", name="Exit"))
    
    # Prompt user to select a torrent
    selected = inquirer.select(
        message="Select a quality:",
        choices=choices,
        default=choices[0] if choices else None,
    ).execute()
    
    if selected == "back":
        return "back"
    elif selected == "exit":
        console.print("[bold blue]Goodbye![/]")
        sys.exit(0)
    
    return selected


def select_download_method(torrent: Dict[str, Any], movie_title: str) -> None:
    """Prompt user to select a download method."""
    # Extract torrent data
    torrent_url = torrent.get("url", "")
    torrent_hash = torrent.get("hash", "")
    quality = torrent.get("quality", "Unknown")
    
    # Create magnet URL using the API client
    client = YTSClient()
    magnet_url = client.construct_magnet_url(torrent_hash, movie_title)
    
    # Create choices for the inquirer prompt
    choices = [
        Choice(value="torrent", name="Download .torrent file"),
        Choice(value="magnet", name="Open magnet link in default torrent app"),
        Choice(value="aria2c", name="Download using aria2c"),
        Choice(value="back", name="← Back"),
        Choice(value="exit", name="Exit")
    ]
    
    while True:
        # Prompt user to select a download method
        selected = inquirer.select(
            message="Select download method:",
            choices=choices,
        ).execute()
        
        if selected == "torrent":
            download_torrent_file(torrent_url, movie_title, quality)
        elif selected == "magnet":
            open_magnet_link(magnet_url)
        elif selected == "aria2c":
            download_with_aria2c(magnet_url)
        elif selected == "back":
            return
        elif selected == "exit":
            console.print("[bold blue]Goodbye![/]")
            sys.exit(0)
        
        # Ask if user wants to try another download method
        continue_choice = inquirer.confirm(
            message="Would you like to try another download method?",
            default=False
        ).execute()
        
        if not continue_choice:
            break


def search_flow() -> None:
    """Interactive flow for searching movies."""
    client = YTSClient()
    
    while True:
        # Prompt user for search query
        query = inquirer.text(
            message="Enter movie name to search (or leave empty to go back):",
            validate=lambda x: True,  # Allow empty input to go back
        ).execute()
        
        if not query:
            return
        
        # Search for movies using the API client
        try:
            # Use the search_movies method from the API client
            response = client.search_movies(query)
            
            # Extract movie data
            movie_count = response.get("movie_count", 0)
            movies = response.get("movies", [])
            
            if movie_count == 0 or not movies:
                console.print(f"[yellow]No movies found for '{query}'.[/]")
                continue
            
            # Display search results
            console.print(f"[bold green]Found {movie_count} movies for '{query}'[/]")
            
            # If only one movie is found, select it automatically
            if movie_count == 1:
                selected_movie = movies[0]
                console.print(f"[bold blue]Selected:[/] {selected_movie.get('title')} ({selected_movie.get('year')})")
            else:
                # Prompt user to select a movie
                selected_movie = select_movie_interactive(movies)
                
                if selected_movie == "back":
                    continue
                elif not selected_movie:
                    continue
            
            # Display movie details
            display_movie_details(selected_movie)
            
            # Display torrent options
            torrents = selected_movie.get("torrents", [])
            display_torrent_options(torrents)
            
            # Prompt user to select a torrent
            selected_torrent = select_torrent_interactive(torrents)
            
            if selected_torrent == "back":
                continue
            elif not selected_torrent:
                continue
            
            # Prompt user to select a download method
            select_download_method(selected_torrent, selected_movie.get("title", "Unknown"))
        
        except YTSAPIError as e:
            logger.error(f"API error: {str(e)}")
            console.print(f"[bold red]Error:[/] {str(e)}")
            continue


def browse_flow() -> None:
    """Interactive flow for browsing latest movies."""
    client = YTSClient()
    
    # Get latest movies using the API client
    try:
        # Use the list_latest_movies method from the API client
        response = client.list_latest_movies(limit=20)
        
        # Extract movie data
        movies = response.get("movies", [])
        
        if not movies:
            console.print("[yellow]No movies found.[/]")
            return
        
        # Display latest movies
        console.print("[bold green]Latest Movies[/]")
        
        while True:
            # Prompt user to select a movie
            selected_movie = select_movie_interactive(movies)
            
            if selected_movie == "back":
                return
            elif not selected_movie:
                return
            
            # Display movie details
            display_movie_details(selected_movie)
            
            # Display torrent options
            torrents = selected_movie.get("torrents", [])
            display_torrent_options(torrents)
            
            # Prompt user to select a torrent
            selected_torrent = select_torrent_interactive(torrents)
            
            if selected_torrent == "back":
                continue
            elif not selected_torrent:
                continue
            
            # Prompt user to select a download method
            select_download_method(selected_torrent, selected_movie.get("title", "Unknown"))
    
    except YTSAPIError as e:
        logger.error(f"API error: {str(e)}")
        console.print(f"[bold red]Error:[/] {str(e)}")
        return


def main_menu() -> None:
    """Display the main menu and handle user selection."""
    while True:
        # Create choices for the inquirer prompt
        choices = [
            Choice(value="search", name="Search for movies"),
            Choice(value="browse", name="Browse latest movies"),
            Choice(value="exit", name="Exit")
        ]
        
        # Prompt user to select an option
        selected = inquirer.select(
            message="What would you like to do?",
            choices=choices,
        ).execute()
        
        if selected == "search":
            search_flow()
        elif selected == "browse":
            browse_flow()
        elif selected == "exit":
            console.print("[bold blue]Goodbye![/]")
            sys.exit(0)


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except errors")
@click.pass_context
def cli(ctx, verbose, quiet):
    """YTS CLI - Search and download movies from YTS.mx"""
    # Configure logging based on verbosity
    if verbose:
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logger.setLevel(logging.ERROR)
    
    # If no command is specified, show the main menu
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold green]YTS CLI[/]\n[blue]Search and download movies from YTS.mx[/]",
            border_style="green"
        ))
        main_menu()


@cli.command()
@click.argument("query", required=False)
def search(query):
    """Search for movies by name."""
    if query:
        client = YTSClient()
        try:
            # Use the search_movies method from the API client
            response = client.search_movies(query)
            
            # Extract movie data
            movie_count = response.get("movie_count", 0)
            movies = response.get("movies", [])
            
            if movie_count == 0 or not movies:
                console.print(f"[yellow]No movies found for '{query}'.[/]")
                return
            
            # Display search results
            console.print(f"[bold green]Found {movie_count} movies for '{query}'[/]")
            
            # Continue with interactive selection
            if movie_count == 1:
                selected_movie = movies[0]
                console.print(f"[bold blue]Selected:[/] {selected_movie.get('title')} ({selected_movie.get('year')})")
            else:
                selected_movie = select_movie_interactive(movies)
                
                if selected_movie == "back" or not selected_movie:
                    search_flow()
                    return
            
            # Display movie details and continue with the flow
            display_movie_details(selected_movie)
            torrents = selected_movie.get("torrents", [])
            display_torrent_options(torrents)
            selected_torrent = select_torrent_interactive(torrents)
            
            if selected_torrent == "back" or not selected_torrent:
                search_flow()
                return
            
            select_download_method(selected_torrent, selected_movie.get("title", "Unknown"))
        
        except YTSAPIError as e:
            logger.error(f"API error: {str(e)}")
            console.print(f"[bold red]Error:[/] {str(e)}")
            search_flow()
    else:
        search_flow()


@cli.command()
def browse():
    """Browse latest movies."""
    browse_flow()


if __name__ == "__main__":
    # Create download directory if it doesn't exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[bold blue]Goodbye![/]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]An unexpected error occurred:[/] {str(e)}")
        sys.exit(1)

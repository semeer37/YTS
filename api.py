"""
YTS API Client

A Python client for interacting with the YTS API to access movie data.
This client provides methods for listing movies, getting movie details,
movie suggestions, and parental guides.
"""

import json
import urllib.parse
from typing import Dict, List, Optional, Union, Any

import requests


class YTSAPIError(Exception):
    """Base exception for YTS API errors."""
    pass


class YTSRequestError(YTSAPIError):
    """Exception raised for errors in the HTTP request."""
    pass


class YTSResponseError(YTSAPIError):
    """Exception raised for errors in the API response."""
    pass


class YTSParameterError(YTSAPIError):
    """Exception raised for invalid parameters."""
    pass


class YTSClient:
    """
    Main client class for interacting with the YTS API.
    
    This client provides methods to access all YTS API endpoints:
    - List Movies
    - Movie Details
    - Movie Suggestions
    - Movie Parental Guides
    
    It handles parameter validation, error handling, and response parsing.
    """
    
    DEFAULT_TRACKERS = [
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:80",
        "udp://tracker.coppersurfer.tk:6969",
        "udp://glotorrents.pw:6969/announce",
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://torrent.gresille.org:80/announce",
        "udp://p4p.arenabg.com:1337",
        "udp://tracker.leechers-paradise.org:6969"
    ]
    
    def __init__(self, base_url: str = "https://yts.mx/api/v2/", timeout: int = 10):
        """
        Initialize the YTS API client.
        
        Args:
            base_url: Base URL for the YTS API. Defaults to "https://yts.mx/api/v2/".
            timeout: Request timeout in seconds. Defaults to 10.
        """
        self.base_url = base_url
        self.timeout = timeout
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make HTTP request to the API and handle errors.
        
        Args:
            endpoint: API endpoint to call.
            params: Query parameters for the request.
            
        Returns:
            Parsed JSON response as a dictionary.
            
        Raises:
            YTSRequestError: If there's an error with the HTTP request.
            YTSResponseError: If the API returns an error response.
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise YTSRequestError(f"Request failed: {str(e)}")
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise YTSResponseError("Failed to parse JSON response")
        
        return self._validate_response(data)
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate API response and handle errors.
        
        Args:
            response: Parsed JSON response.
            
        Returns:
            Validated response data.
            
        Raises:
            YTSResponseError: If the API returns an error status.
        """
        if response.get("status") != "ok":
            error_message = response.get("status_message", "Unknown API error")
            raise YTSResponseError(f"API error: {error_message}")
        
        return response.get("data", {})
    
    def _validate_integer(self, value: Any, param_name: str, 
                          min_value: Optional[int] = None, 
                          max_value: Optional[int] = None) -> Optional[int]:
        """
        Validate integer parameters.
        
        Args:
            value: Value to validate.
            param_name: Name of the parameter (for error messages).
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.
            
        Returns:
            Validated integer value or None.
            
        Raises:
            YTSParameterError: If validation fails.
        """
        if value is None:
            return None
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise YTSParameterError(f"Parameter '{param_name}' must be an integer")
        
        if min_value is not None and int_value < min_value:
            raise YTSParameterError(f"Parameter '{param_name}' must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise YTSParameterError(f"Parameter '{param_name}' must be at most {max_value}")
        
        return int_value
    
    def _validate_string(self, value: Any, param_name: str, 
                         allowed_values: Optional[List[str]] = None) -> Optional[str]:
        """
        Validate string parameters.
        
        Args:
            value: Value to validate.
            param_name: Name of the parameter (for error messages).
            allowed_values: List of allowed values.
            
        Returns:
            Validated string value or None.
            
        Raises:
            YTSParameterError: If validation fails.
        """
        if value is None:
            return None
        
        if not isinstance(value, str):
            raise YTSParameterError(f"Parameter '{param_name}' must be a string")
        
        if allowed_values and value not in allowed_values:
            allowed_str = ", ".join(allowed_values)
            raise YTSParameterError(f"Parameter '{param_name}' must be one of: {allowed_str}")
        
        return value
    
    def _validate_boolean(self, value: Any, param_name: str) -> Optional[bool]:
        """
        Validate boolean parameters.
        
        Args:
            value: Value to validate.
            param_name: Name of the parameter (for error messages).
            
        Returns:
            Validated boolean value or None.
            
        Raises:
            YTSParameterError: If validation fails.
        """
        if value is None:
            return None
        
        if not isinstance(value, bool):
            raise YTSParameterError(f"Parameter '{param_name}' must be a boolean")
        
        return value
    
    def _validate_required(self, value: Any, param_name: str) -> Any:
        """
        Validate that a required parameter is provided.
        
        Args:
            value: Value to validate.
            param_name: Name of the parameter (for error messages).
            
        Returns:
            The provided value.
            
        Raises:
            YTSParameterError: If the value is None.
        """
        if value is None:
            raise YTSParameterError(f"Parameter '{param_name}' is required")
        
        return value
    
    def construct_magnet_url(self, hash_value: str, title: str, 
                            trackers: Optional[List[str]] = None) -> str:
        """
        Construct a magnet URL from torrent hash and title.
        
        Args:
            hash_value: Torrent hash.
            title: Movie title.
            trackers: List of tracker URLs. If None, default trackers will be used.
            
        Returns:
            Constructed magnet URL.
        """
        if trackers is None:
            trackers = self.DEFAULT_TRACKERS
        
        # URL encode the title
        encoded_title = urllib.parse.quote(title)
        
        # Start with the basic magnet link
        magnet = f"magnet:?xt=urn:btih:{hash_value}&dn={encoded_title}"
        
        # Add trackers
        for tracker in trackers:
            magnet += f"&tr={urllib.parse.quote(tracker)}"
        
        return magnet
    
    def list_movies(self, limit: int = 20, page: int = 1, 
                   quality: Optional[str] = None, minimum_rating: int = 0, 
                   query_term: Optional[str] = None, genre: Optional[str] = None, 
                   sort_by: str = "date_added", order_by: str = "desc", 
                   with_rt_ratings: bool = False) -> Dict[str, Any]:
        """
        List and search movies with various filters and sorting options.
        
        Args:
            limit: Number of results per page (1-50). Defaults to 20.
            page: Page number for pagination. Defaults to 1.
            quality: Filter by quality (480p, 720p, 1080p, 1080p.x265, 2160p, 3D).
            minimum_rating: Filter by minimum IMDb rating (0-9). Defaults to 0.
            query_term: Search term for movies, actors, directors.
            genre: Filter by genre.
            sort_by: Sort results by (title, year, rating, peers, seeds, 
                    download_count, like_count, date_added). Defaults to "date_added".
            order_by: Order results (desc, asc). Defaults to "desc".
            with_rt_ratings: Include Rotten Tomatoes ratings. Defaults to False.
            
        Returns:
            Dictionary containing movie list data.
        """
        # Validate parameters
        limit = self._validate_integer(limit, "limit", 1, 50)
        page = self._validate_integer(page, "page", 1)
        minimum_rating = self._validate_integer(minimum_rating, "minimum_rating", 0, 9)
        
        quality_options = ["480p", "720p", "1080p", "1080p.x265", "2160p", "3D"]
        quality = self._validate_string(quality, "quality", quality_options)
        
        sort_options = ["title", "year", "rating", "peers", "seeds", 
                       "download_count", "like_count", "date_added"]
        sort_by = self._validate_string(sort_by, "sort_by", sort_options)
        
        order_options = ["desc", "asc"]
        order_by = self._validate_string(order_by, "order_by", order_options)
        
        with_rt_ratings = self._validate_boolean(with_rt_ratings, "with_rt_ratings")
        
        # Build parameters
        params = {
            "limit": limit,
            "page": page,
            "minimum_rating": minimum_rating,
            "sort_by": sort_by,
            "order_by": order_by,
        }
        
        if quality:
            params["quality"] = quality
        
        if query_term:
            params["query_term"] = query_term
        
        if genre:
            params["genre"] = genre
        
        if with_rt_ratings:
            params["with_rt_ratings"] = "true"
        
        # Make request
        return self._make_request("list_movies.json", params)
    
    def search_movies(self, query_term: str, limit: int = 20, page: int = 1) -> Dict[str, Any]:
        """
        Search for movies by name.
        
        Args:
            query_term: Search term for movies, actors, directors.
            limit: Number of results per page (1-50). Defaults to 20.
            page: Page number for pagination. Defaults to 1.
            
        Returns:
            Dictionary containing search results.
        """
        return self.list_movies(query_term=query_term, limit=limit, page=page)
    
    def list_latest_movies(self, limit: int = 20, page: int = 1) -> Dict[str, Any]:
        """
        List latest movies.
        
        Args:
            limit: Number of results per page (1-50). Defaults to 20.
            page: Page number for pagination. Defaults to 1.
            
        Returns:
            Dictionary containing latest movies.
        """
        return self.list_movies(limit=limit, page=page, sort_by="date_added", order_by="desc")
    
    def movie_details(self, movie_id: Optional[int] = None, 
                     imdb_id: Optional[str] = None, 
                     with_images: bool = False, 
                     with_cast: bool = False) -> Dict[str, Any]:
        """
        Get detailed information about a specific movie.
        
        Args:
            movie_id: YTS ID of the movie.
            imdb_id: IMDB ID of the movie.
            with_images: Include image URLs in response. Defaults to False.
            with_cast: Include cast information in response. Defaults to False.
            
        Returns:
            Dictionary containing movie details.
            
        Raises:
            YTSParameterError: If neither movie_id nor imdb_id is provided.
        """
        # Validate parameters
        if movie_id is None and imdb_id is None:
            raise YTSParameterError("Either 'movie_id' or 'imdb_id' is required")
        
        with_images = self._validate_boolean(with_images, "with_images")
        with_cast = self._validate_boolean(with_cast, "with_cast")
        
        # Build parameters
        params = {}
        
        if movie_id is not None:
            params["movie_id"] = self._validate_integer(movie_id, "movie_id", 1)
        
        if imdb_id is not None:
            params["imdb_id"] = imdb_id
        
        if with_images:
            params["with_images"] = "true"
        
        if with_cast:
            params["with_cast"] = "true"
        
        # Make request
        return self._make_request("movie_details.json", params)
    
    def movie_suggestions(self, movie_id: int) -> Dict[str, Any]:
        """
        Get movie suggestions related to a specific movie.
        
        Args:
            movie_id: ID of the movie.
            
        Returns:
            Dictionary containing movie suggestions.
        """
        # Validate parameters
        movie_id = self._validate_required(movie_id, "movie_id")
        movie_id = self._validate_integer(movie_id, "movie_id", 1)
        
        # Build parameters
        params = {"movie_id": movie_id}
        
        # Make request
        return self._make_request("movie_suggestions.json", params)
    
    def movie_parental_guides(self, movie_id: int) -> Dict[str, Any]:
        """
        Get parental guide information for a specific movie.
        
        Args:
            movie_id: ID of the movie.
            
        Returns:
            Dictionary containing parental guide information.
        """
        # Validate parameters
        movie_id = self._validate_required(movie_id, "movie_id")
        movie_id = self._validate_integer(movie_id, "movie_id", 1)
        
        # Build parameters
        params = {"movie_id": movie_id}
        
        # Make request
        return self._make_request("movie_parental_guides.json", params)
    
    def download_torrent_file(self, url: str, file_path: str) -> bool:
        """
        Download a torrent file from the given URL.
        
        Args:
            url: URL of the torrent file.
            file_path: Path where the file should be saved.
            
        Returns:
            True if download was successful, False otherwise.
            
        Raises:
            YTSRequestError: If there's an error with the HTTP request.
        """
        try:
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
        
        except requests.RequestException as e:
            raise YTSRequestError(f"Failed to download torrent file: {str(e)}")
        except IOError as e:
            raise YTSRequestError(f"Failed to save torrent file: {str(e)}")
                          

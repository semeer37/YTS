# YTS API Documentation 

## Overview
The YTS API is a REST interface that provides access to the YTS website's movie database. It supports JSON, JSONP, and XML formats.

## Common Response Structure
All API endpoints return the same data structure:

| Key | Description | Example |
|-----|-------------|---------|
| status | The returned status for the API call | "ok" or "error" |
| status_message | Success or error message | "Query was successful" |
| data | If status is "ok", contains the API query results | (object) |

## Endpoints

### 1. List Movies
**HTTP GET**: `https://yts.mx/api/v2/list_movies.json`

Used to list and search through all available movies with sorting, filtering, and pagination options.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| limit | No | Integer (1-50) | 20 | Results per page |
| page | No | Integer | 1 | Page number for pagination |
| quality | No | String | All | Filter by quality (480p, 720p, 1080p, 1080p.x265, 2160p, 3D) |
| minimum_rating | No | Integer (0-9) | 0 | Filter by minimum IMDb rating |
| query_term | No | String | 0 | Search term for movies, actors, directors |
| genre | No | String | All | Filter by genre |
| sort_by | No | String | date_added | Sort results (title, year, rating, peers, seeds, download_count, like_count, date_added) |
| order_by | No | String | desc | Order results (desc, asc) |
| with_rt_ratings | No | Boolean | false | Include Rotten Tomatoes ratings |

**Response Data:**

| Key | Description |
|-----|-------------|
| movie_count | Total movie count for the query |
| limit | Results per page limit |
| page_number | Current page number |
| movies | Array of movie objects |

**Note:** Magnet URLs need to be constructed manually using the torrent hash.

### 2. Movie Details
**HTTP GET**: `https://yts.mx/api/v2/movie_details.json`

Returns detailed information about a specific movie.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| movie_id or imdb_id | Yes | Integer | null | YTS ID or IMDB ID of the movie |
| with_images | No | Boolean | false | Include image URLs in response |
| with_cast | No | Boolean | false | Include cast information in response |

**Note:** Magnet URLs need to be constructed manually using the torrent hash.

### 3. Movie Suggestions
**HTTP GET**: `https://yts.mx/api/v2/movie_suggestions.json`

Returns 4 related movies as suggestions.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| movie_id | Yes | Integer | null | ID of the movie |

### 4. Movie Parental Guides
**HTTP GET**: `https://yts.mx/api/v2/movie_parental_guides.json`

Returns all parental guide ratings for the specified movie.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| movie_id | Yes | Integer | null | ID of the movie |

## Implementation Considerations

1. **Base URL**: All endpoints share the base URL `https://yts.mx/api/v2/`
2. **Response Format**: Support for JSON, JSONP, and XML (we'll focus on JSON for the Python client)
3. **Error Handling**: Need to check the "status" field in responses
4. **Parameter Validation**: Validate parameter types and ranges before making requests
5. **Magnet URL Construction**: Helper method to construct magnet URLs from torrent hashes

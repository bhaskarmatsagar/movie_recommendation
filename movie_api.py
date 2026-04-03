from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
import os
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for Express.js to access this API

# TMDB API Configuration
# You can use EITHER the API Key OR the Read Access Token (both work)
TMDB_API_KEY = 'YOUR_TMDB_API_KEY_HERE'  # Replace with your API key (v3)
TMDB_READ_TOKEN = 'YOUR_TMDB_READ_TOKEN_HERE'  # OR use Read Access Token (v4 - recommended)

TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

# Load the pickled files
try:
    with open('movies_dict.pkl', 'rb') as file:
        movies_dict = pickle.load(file)
    
    with open('similarity.pkl', 'rb') as file:
        similarity = pickle.load(file)
    
    # Convert to DataFrame if it's a dict
    if isinstance(movies_dict, dict):
        movies_df = pd.DataFrame(movies_dict)
    else:
        movies_df = movies_dict
    
    print("✓ Movies data loaded successfully")
    print(f"✓ Total movies: {len(movies_df)}")
    print("✓ Similarity matrix loaded successfully")
    
    # Check what columns are available
    print(f"✓ Available columns: {list(movies_df.columns)}")
    
except FileNotFoundError as e:
    print(f"✗ Error: {e}")
    print("Make sure movies_dict.pkl and similarity.pkl are in the same directory")
    movies_df = None
    similarity = None
except Exception as e:
    print(f"✗ Error loading files: {e}")
    movies_df = None
    similarity = None


def fetch_movie_poster(movie_title, movie_id=None):
    """
    Fetch movie poster from TMDB API
    Supports both API Key (v3) and Read Access Token (v4)
    """
    try:
        # Check if TMDB is configured
        has_api_key = TMDB_API_KEY != 'YOUR_TMDB_API_KEY_HERE'
        has_token = TMDB_READ_TOKEN != 'YOUR_TMDB_READ_TOKEN_HERE'
        
        if not has_api_key and not has_token:
            return ''  # Return empty if neither configured
        
        # Prepare headers and params
        headers = {}
        params = {
            'query': movie_title,
            'language': 'en-US'
        }
        
        # Use Read Access Token if available (preferred method)
        if has_token:
            headers['Authorization'] = f'Bearer {TMDB_READ_TOKEN}'
        else:
            # Fallback to API Key
            params['api_key'] = TMDB_API_KEY
        
        # Search for the movie
        search_url = f"{TMDB_BASE_URL}/search/movie"
        response = requests.get(search_url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data['results'] and len(data['results']) > 0:
                poster_path = data['results'][0].get('poster_path')
                if poster_path:
                    return f"{TMDB_IMAGE_BASE_URL}{poster_path}"
        elif response.status_code == 401:
            print(f"⚠️ TMDB Authentication failed - check your API key or token")
        
        return ''
    except Exception as e:
        print(f"Error fetching poster for {movie_title}: {e}")
        return ''


def get_recommendations(movie_name, num_recommendations=5):
    """
    Get movie recommendations based on similarity
    """
    if movies_df is None or similarity is None:
        raise Exception("Data not loaded properly")
    
    # Find the movie in the dataset (case-insensitive)
    movie_name_lower = movie_name.lower()
    
    # Try exact match first
    movie_indices = movies_df[movies_df['title'].str.lower() == movie_name_lower].index
    
    # If no exact match, try partial match
    if len(movie_indices) == 0:
        movie_indices = movies_df[movies_df['title'].str.lower().str.contains(movie_name_lower, na=False)].index
    
    if len(movie_indices) == 0:
        raise Exception(f"Movie '{movie_name}' not found in database")
    
    # Get the index of the first matching movie
    movie_idx = movie_indices[0]
    
    # Get similarity scores for this movie
    similarity_scores = list(enumerate(similarity[movie_idx]))
    
    # Sort by similarity (descending) and get top N+1 (excluding the movie itself)
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
    
    # Get top N recommendations (skip first one as it's the movie itself)
    top_movies = similarity_scores[1:num_recommendations+1]
    
    # Get movie details
    recommendations = []
    for idx, score in top_movies:
        movie = movies_df.iloc[idx]
        movie_title = movie['title']
        
        # Try to get poster from different sources
        poster_url = ''
        
        # 1. Check if poster_path exists in your data
        if 'poster_path' in movie and movie.get('poster_path') and str(movie.get('poster_path')) != 'nan':
            poster_path = str(movie['poster_path']).strip()
            if poster_path.startswith('/'):
                poster_path = poster_path[1:]
            poster_url = f"{TMDB_IMAGE_BASE_URL}/{poster_path}"
        
        # 2. If no poster in data, fetch from TMDB API (if configured)
        if not poster_url:
            has_api_key = TMDB_API_KEY != 'YOUR_TMDB_API_KEY_HERE'
            has_token = TMDB_READ_TOKEN != 'YOUR_TMDB_READ_TOKEN_HERE'
            
            if has_api_key or has_token:
                poster_url = fetch_movie_poster(movie_title, movie.get('movie_id'))
        
        # 3. Use placeholder if still no poster
        if not poster_url:
            poster_url = f"https://via.placeholder.com/500x750/667eea/ffffff?text={movie_title.replace(' ', '+')}"
        
        recommendations.append({
            'title': movie_title,
            'movie_id': int(movie.get('movie_id', idx)) if 'movie_id' in movie else idx,
            'overview': movie.get('overview', 'No overview available'),
            'poster_url': poster_url,
            'release_date': str(movie.get('release_date', '')) if 'release_date' in movie else '',
            'vote_average': float(movie.get('vote_average', 0)) if 'vote_average' in movie else 0,
            'similarity_score': float(score)
        })
    
    return recommendations


@app.route('/recommend', methods=['GET'])
def recommend():
    """
    API endpoint to get movie recommendations
    Query parameter: movie (required)
    """
    try:
        movie_name = request.args.get('movie')
        
        if not movie_name:
            return jsonify({
                'error': 'Movie name is required',
                'message': 'Please provide a movie name using ?movie=MovieName'
            }), 400
        
        # Get recommendations
        recommendations = get_recommendations(movie_name)
        
        return jsonify(recommendations), 200
        
    except Exception as e:
        error_message = str(e)
        status_code = 404 if 'not found' in error_message.lower() else 500
        
        return jsonify({
            'error': error_message,
            'message': 'Failed to get recommendations'
        }), status_code


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    has_api_key = TMDB_API_KEY != '87f2a6fba552fc37f82a2f159502380f'
    has_token = TMDB_READ_TOKEN != 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI4N2YyYTZmYmE1NTJmYzM3ZjgyYTJmMTU5NTAyMzgwZiIsIm5iZiI6MTc2MTYyOTg0Ni45NzYsInN1YiI6IjY5MDA1Njk2MGJlNjM2OTgzYWE2MzZlMiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.EN2Ri3EjiFDtkxaM9ZL0xSM32dXBnf_Uts84KAi4F30'
    
    return jsonify({
        'status': 'healthy',
        'movies_loaded': movies_df is not None,
        'total_movies': len(movies_df) if movies_df is not None else 0,
        'tmdb_configured': has_api_key or has_token,
        'tmdb_method': 'token' if has_token else ('api_key' if has_api_key else 'none')
    }), 200


@app.route('/movies', methods=['GET'])
def get_movies():
    """Get list of all available movies"""
    try:
        if movies_df is None:
            return jsonify({'error': 'Movies data not loaded'}), 500
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        search = request.args.get('search', '', type=str)
        
        # Filter movies if search term provided
        if search:
            filtered_df = movies_df[movies_df['title'].str.contains(search, case=False, na=False)]
        else:
            filtered_df = movies_df
        
        # Limit results
        filtered_df = filtered_df.head(limit)
        
        # Convert to list of dicts
        movies_list = []
        for _, movie in filtered_df.iterrows():
            movies_list.append({
                'title': movie['title'],
                'movie_id': int(movie.get('movie_id', 0)) if 'movie_id' in movie else 0,
                'overview': movie.get('overview', '')[:200] + '...' if 'overview' in movie and len(str(movie.get('overview', ''))) > 200 else movie.get('overview', ''),
            })
        
        return jsonify({
            'total': len(movies_list),
            'movies': movies_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if movies_df is None or similarity is None:
        print("\n⚠️  Warning: Data files not loaded properly!")
        print("The server will start but recommendations won't work.")
        print("\nMake sure these files exist:")
        print("  - movies_dict.pkl")
        print("  - similarity.pkl")
    
    has_api_key = TMDB_API_KEY != 'YOUR_TMDB_API_KEY_HERE'
    has_token = TMDB_READ_TOKEN != 'YOUR_TMDB_READ_TOKEN_HERE'
    
    if not has_api_key and not has_token:
        print("\n⚠️  TMDB API not configured!")
        print("To get real movie posters:")
        print("  1. Go to: https://www.themoviedb.org/settings/api")
        print("  2. Copy your 'API Read Access Token (v4)' OR 'API Key (v3)'")
        print("  3. Replace in movie_api.py:")
        print("     TMDB_READ_TOKEN = 'your_token_here'  # Recommended")
        print("     OR")
        print("     TMDB_API_KEY = 'your_api_key_here'")
        print("  4. Without configuration, placeholder images will be used\n")
    elif has_token:
        print("\n✓ TMDB configured with Read Access Token (v4)")
    else:
        print("\n✓ TMDB configured with API Key (v3)")
    
    print(f"\n🚀 Starting Flask API on http://localhost:5000")
    print(f"📊 Available endpoints:")
    print(f"   GET /recommend?movie=MovieName")
    print(f"   GET /health")
    print(f"   GET /movies?search=query&limit=100\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
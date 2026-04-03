import streamlit as st
import pandas as pd
import pickle
import numpy as np
from datetime import datetime
import requests
from PIL import Image
import io

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="🎬 Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Movie Recommendation System")
st.markdown("Get **Top 5 similar movies** instantly 🎯")


import os

SIMILARITY_URL = "https://drive.google.com/uc?id=1QNPUjsdYW88YLwa3qnSZyd45ivNCxv3a"
def download_file(url, filename):
    if not os.path.exists(filename):
        response = requests.get(url)
        with open(filename, "wb") as f:
            f.write(response.content)

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    try:
        with open("movies_dict.pkl", "rb") as f:
            movies_dict = pickle.load(f)

        # FIX: convert dict → DataFrame
        if isinstance(movies_dict, dict):
            movies_df = pd.DataFrame(movies_dict)
        else:
            movies_df = movies_dict

        download_file(SIMILARITY_URL, "similarity.pkl")

        with open("similarity.pkl", "rb") as f:
            similarity = pickle.load(f)

        return movies_df, similarity

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()

movies_df, similarity = load_data()

# ---------------- TMDB CONFIG ----------------
TMDB_API_KEY = "87f2a6fba552fc37f82a2f159502380f"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def fetch_poster(movie_title):
    try:
        params = {"query": movie_title, "api_key": TMDB_API_KEY}
        res = requests.get(f"{TMDB_BASE_URL}/search/movie", params=params, timeout=5)

        if res.status_code == 200:
            data = res.json()
            if data["results"]:
                poster_path = data["results"][0].get("poster_path")
                if poster_path:
                    return f"{TMDB_IMAGE_BASE_URL}{poster_path}"
    except:
        pass

    return "https://via.placeholder.com/300x450?text=No+Image"


# ---------------- RECOMMENDATION ----------------
def get_recommendations(movie_name):
    movie_name = movie_name.lower()

    # exact match
    indices = movies_df[movies_df["title"].str.lower() == movie_name].index

    # partial match
    if len(indices) == 0:
        indices = movies_df[
            movies_df["title"].str.lower().str.contains(movie_name, na=False)
        ].index

    if len(indices) == 0:
        raise ValueError("Movie not found!")

    idx = indices[0]

    sim_scores = list(enumerate(similarity[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    recommendations = []
    for i, score in sim_scores[1:6]:
        movie = movies_df.iloc[i]

        recommendations.append(
            {
                "title": movie["title"],
                "poster": fetch_poster(movie["title"]),
                "rating": float(movie.get("vote_average", 0)),
                "similarity": round(score * 100, 0),
                "overview": str(movie.get("overview", "No overview"))[:120] + "...",
            }
        )

    return recommendations


# ---------------- SESSION STATE ----------------
if "history" not in st.session_state:
    st.session_state.history = []


def save_history(movie, recs):
    st.session_state.history.insert(
        0,
        {
            "movie": movie,
            "time": datetime.now().strftime("%H:%M:%S"),
            "count": len(recs),
        },
    )
    st.session_state.history = st.session_state.history[:5]


# ---------------- SIDEBAR ----------------
st.sidebar.header("🔍 Search")

movie_list = movies_df["title"].values

selected_movie = st.sidebar.selectbox("Select a movie", movie_list)

if st.sidebar.button("🎥 Recommend", use_container_width=True):
    with st.spinner("Finding recommendations..."):
        try:
            recs = get_recommendations(selected_movie)
            save_history(selected_movie, recs)
            st.session_state["recs"] = recs
            st.session_state["selected"] = selected_movie
        except Exception as e:
            st.error(str(e))

if st.sidebar.button("🗑️ Clear History"):
    st.session_state.history = []
    st.rerun()

# ---------------- MAIN ----------------
if "recs" in st.session_state:

    st.subheader(f"✨ Recommendations for **{st.session_state['selected']}**")

    cols = st.columns(5)

    for i, rec in enumerate(st.session_state["recs"]):
        with cols[i]:
            try:
                img = Image.open(
                    io.BytesIO(requests.get(rec["poster"], timeout=5).content)
                )
                st.image(img, use_column_width=True)
            except:
                st.image(rec["poster"], use_column_width=True)

            st.markdown(f"**{rec['title']}**")
            st.metric("⭐ Rating", f"{rec['rating']:.1f}")
            st.metric("🔗 Similarity", f"{rec['similarity']}%")
            st.caption(rec["overview"])

# ---------------- HISTORY ----------------
st.markdown("---")
st.subheader("📜 Recent Searches")

if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No history yet")

# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown(
    "<center>Built with ❤️ using Streamlit</center>",
    unsafe_allow_html=True,
)
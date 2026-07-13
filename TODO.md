# Movie Recommendation Streamlit Refactor - TODO

## Approved Plan Steps:

### 1. ✅ Create app.py (main Streamlit app)
- Load data from python-api/ pkl files
- Implement get_recommendations()
- UI: sidebar input, rec cards, history w/ session state
- Loading spinner, clear history

### 2. Update requirements.txt
- Add streamlit
- Remove Flask/CORS
- Keep pandas/numpy/sklearn/requests

### 3. Cleanup frontend files
- Delete public/, routes/, utils/, server.js, package*.json
- Delete movie_api.py (logic moved)
- Keep python-api/ pkl/CSVs
- Delete .git*, README.md

### 4. Test & Complete
- pip install -r requirements.txt
- streamlit run app.py
- Verify recs/history/UI
- attempt_completion

**Progress: 0/4**

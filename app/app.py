from flask import Flask, render_template, request
import joblib
import re
import scipy.sparse as sp
import numpy as np

app = Flask(__name__)

model = joblib.load("../models/random_forest_fixed.pkl")
vectorizer = joblib.load("../models/tfidf_vectorizer_fixed.pkl")

# Get the feature names for explanation
feature_names = vectorizer.get_feature_names_out().tolist() + ['char_length', 'url_count']
importances = model.feature_importances_

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        email_text = request.form['email_text']
        
        char_len = len(email_text)
        url_count = len(re.findall(r'http|www', email_text))
        
        # Vectorize
        text_tfidf = vectorizer.transform([email_text])
        struct_feats = sp.csr_matrix([[char_len, url_count]])
        final_features = sp.hstack((text_tfidf, struct_feats))
        
        prediction = int(model.predict(final_features)[0])
        probabilities = model.predict_proba(final_features)[0]
        confidence = round(probabilities[prediction] * 100, 2)
        
        # --- EXPLANATION LOGIC ---
        # Find which words from the email are actually in our vocabulary
        # and rank them by how important the model thinks they are.
        suspicious_words = []
        if prediction == 1:
            # Get the non-zero features from the TF-IDF (words present in this email)
            dense_tfidf = text_tfidf.toarray()[0]
            present_indices = np.where(dense_tfidf > 0)[0]
            
            # Sort those words by the model's global feature importance
            word_importances = [(feature_names[i], importances[i]) for i in present_indices]
            word_importances.sort(key=lambda x: x[1], reverse=True)
            
            # Grab the top 5 most "suspicious" words
            suspicious_words = [word for word, imp in word_importances[:5]]
        
        return render_template('index.html', 
                               prediction=prediction, 
                               confidence=confidence,
                               char_len=char_len,
                               url_count=url_count,
                               suspicious_words=suspicious_words)
    
    return render_template('index.html', prediction=None)

if __name__ == '__main__':
    app.run(debug=True)
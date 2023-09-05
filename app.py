from flask import Flask, render_template, request
import tensorflow as tf
import numpy as np
import base64
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


app = Flask(__name__)

_model = tf.keras.models.load_model('py-file/Model-Skin.h5')
_classes = ['brown', 'dark', 'light', 'medium', 'pale']

data = pd.read_csv('data/Products.csv')

mapping = {1 : 'pale', 2: 'light', 3: 'medium', 4: 'brown', 5: 'dark'}
data['skintone'] = data['SkintoneId'].map(mapping)

# Menggabungkan deskripsi produk menjadi satu teks
data['overview'] = data['namaProduk'] + ' ' + data['skinType'] + ' ' + \
                data['colorRange'] + ' ' + data['skintone']
print(data)

vectorizer = CountVectorizer()
tfidf_matrix = vectorizer.fit_transform(data['overview'])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
cosine_sim_df = pd.DataFrame(cosine_sim)

print(cosine_sim_df)

@app.route('/')
def index():
    return render_template('index.html', show_modal=True)


def content_recommendation(keyword):
    a = data.copy().reset_index().drop('index',axis=1)
    relevant_products = a[a['overview'].str.contains(keyword, case=False)]
    if relevant_products.empty:
        return "Tidak ada produk yang cocok dengan kata khusus yang diberikan."

    relevant_indices = relevant_products.index.tolist()
    cosine_similarities = cosine_sim_df[relevant_indices].mean(axis=1)
    top_n_indices = cosine_similarities.nlargest(10).index

    similar_df = a.iloc[top_n_indices][['namaProduk',
                                        'imageUrl',
                                        'harga',
                                        'skinType',
                                        'colorRange',
                                        'SkintoneId',
                                        'overview']]
    similar_df['cosine_similarity'] = cosine_similarities.iloc[top_n_indices]
    return similar_df

@app.route('/prediction', methods=['GET','POST'])

def foundation_recommendation():
    img_uploaded = None
    probability = None 
    class_pred = None
    guestName = None
    recommendation_df = None

    if request.method=='POST':
        guestName = request.form['guestName']
        file = request.files['file']

        img_bytes = file.read()
        img = tf.image.decode_jpeg(img_bytes, channels=3)
        img = tf.image.convert_image_dtype(img, tf.float32)
        img = tf.image.resize(img, [224, 224])
        img = np.expand_dims(img, axis=0)
        
        animals_pred = _model.predict(img, verbose=0)
        index = np.argmax(animals_pred[0])
        probability= round(animals_pred[0][index]*100, 2)
        class_pred = _classes[index]
        print(class_pred, '<<< class_pred')
        print(probability , '<<< prob')

        img_uploaded = base64.b64encode(img_bytes).decode('utf-8')
        
        req = content_recommendation(str(class_pred))
        print(req, '<<< pred')
        
        recommendation_df = req.to_dict('records')


    return render_template('fetch-data.html', user=guestName, skintone=class_pred, recommendation_df=recommendation_df)




if __name__ == '__main__':
    app.run(debug=True)
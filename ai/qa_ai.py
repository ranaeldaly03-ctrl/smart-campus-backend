from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def answer_question(question, text):
    sentences = [s.strip() for s in text.split(".") if len(s) > 20]

    if not sentences:
        return "المحتوى غير متاح"

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(sentences + [question])

    similarity = cosine_similarity(tfidf[-1], tfidf[:-1])
    best = similarity.argmax()

    if similarity[0][best] < 0.2:
        return "مش لاقية إجابة واضحة في المحتوى"

    return sentences[best]

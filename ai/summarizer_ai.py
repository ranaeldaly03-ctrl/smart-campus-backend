from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

def summarize(text, ratio=0.3):
    sentences = [s.strip() for s in text.split(".") if len(s) > 25]

    if not sentences:
        return "لا يوجد محتوى للتلخيص"

    tfidf = TfidfVectorizer().fit_transform(sentences)
    scores = tfidf.sum(axis=1).A1

    ranked = np.argsort(scores)[::-1]
    size = max(1, int(len(sentences) * ratio))
    selected = sorted(ranked[:size])

    return ". ".join(sentences[i] for i in selected)

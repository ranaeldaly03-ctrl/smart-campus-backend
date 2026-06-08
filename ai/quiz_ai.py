import random
import re

def generate_mcq(text, num_questions=5):

    
    text = re.sub(r'\s+', ' ', text)

    
    sentences = re.split(r'[.!؟]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]

    if len(sentences) < num_questions:
        num_questions = len(sentences)

    questions = []

    for i in range(num_questions):

        sentence = sentences[i]
        words = sentence.split()

        if len(words) < 6:
            continue

        blank_index = random.randint(2, len(words)-2)
        correct_answer = words[blank_index]

        words[blank_index] = "_____"
        question_text = " ".join(words)

        options = set()
        options.add(correct_answer)

        while len(options) < 4:
            w = random.choice(words)
            if w != "_____":
                options.add(w)

        options = list(options)
        random.shuffle(options)

        questions.append({
            "question": question_text,
            "options": options,
            "correct": correct_answer
        })

    return questions
import json
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Embedding, Conv1D, LSTM
from tensorflow.keras.optimizers import Adam
import random
import pickle
import re

# Download required NLTK data
nltk.download('punkt')
nltk.download('wordnet')

# Initialize lemmatizer
lemmatizer = WordNetLemmatizer()

# Load intents file
try:
    with open('intents.json', 'r') as file:
        intents = json.load(file)
except Exception as e:
    print(f"Error loading intents file: {e}")
    intents = {"intents": []}

# Prepare data
words = []
classes = []
documents = []
ignore_words = ['?', '!', '.', ',']

for intent in intents['intents']:
    for pattern in intent['patterns']:
        # Remove punctuation
        pattern = re.sub(r'[^\w\s]', '', pattern)
        word_list = nltk.word_tokenize(pattern)
        words.extend(word_list)
        documents.append((word_list, intent['tag']))
        if intent['tag'] not in classes:
            classes.append(intent['tag'])

# Lemmatize, lowercase, and deduplicate words
words = [lemmatizer.lemmatize(w.lower()) for w in words if w not in ignore_words]
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

print(f"{len(documents)} documents")
print(f"{len(classes)} classes: {classes}")
print(f"{len(words)} unique lemmatized words: {words}")

# Save words and classes
try:
    pickle.dump(words, open('words.pkl', 'wb'))
    pickle.dump(classes, open('classes.pkl', 'wb'))
    print("Words and classes saved to pickle files.")
except Exception as e:
    print(f"Error saving pickle files: {e}")

# Create training data
max_sequence_length = 20
training = []
output_empty = [0] * len(classes)

for doc in documents:
    word_patterns = doc[0]
    word_patterns = [lemmatizer.lemmatize(word.lower()) for word in word_patterns]
    if len(word_patterns) < max_sequence_length:
        word_patterns += [''] * (max_sequence_length - len(word_patterns))
    else:
        word_patterns = word_patterns[:max_sequence_length]

    word_indices = [words.index(word) if word in words else 0 for word in word_patterns]
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([word_indices, output_row])

# Shuffle and convert to numpy arrays
random.shuffle(training)
training = np.array(training, dtype=object)

train_x = np.array(list(training[:, 0]), dtype=np.float32)
train_y = np.array(list(training[:, 1]), dtype=np.float32)

# Build model: CNN + LSTM (without GlobalMaxPooling1D)
model = Sequential()
model.add(Embedding(input_dim=len(words) + 1, output_dim=128))  # Removed input_length
model.add(Conv1D(128, 5, activation='relu'))
model.add(LSTM(128, return_sequences=False))
model.add(Dropout(0.5))
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation='softmax'))

# Compile and train the model
model.compile(optimizer=Adam(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])

try:
    hist = model.fit(train_x, train_y, epochs=100, batch_size=32, verbose=2)
    model.save('chatbot_model.h5')
    print("Hybrid model trained and saved successfully.")
except Exception as e:
    print(f"Error training or saving the model: {e}")

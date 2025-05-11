import json
import random
import numpy as np
import nltk
import pickle
from autocorrect import Speller
from nltk.stem import WordNetLemmatizer
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import Adam
from keras.models import load_model
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure Gemini API with proper model name
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or 'AIzaSyCzgAFXz01xdHcTEHbNb0zd5hyK3jA0gdQ'
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the correct model name
try:
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception as e:
    print(f"Error with gemini-1.5-pro-latest: {e}")
    try:
        gemini_model = genai.GenerativeModel('gemini-pro')
    except Exception as fallback_e:
        print(f"Error with gemini-pro: {fallback_e}")
        gemini_model = None

nltk.download("punkt")
nltk.download("wordnet")

# Lemmatizer
lemmatizer = WordNetLemmatizer()

# load intents
with open("intents.json") as file:
    intents = json.load(file)

try:  # load saved model if existed
    with open("data.pickle", "rb") as f:
        words, classes, training, output = pickle.load(f)
    model = load_model("chatbot-model.h5")
except:  # create new model if not existed
    # create list of words, tags, and tuples (pattern+tag), and ignore words
    words = []
    classes = []
    documents = []
    ignore_words = ["?", "!", ".", ","]

    # loop through intents and patterns
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            word_list = nltk.word_tokenize(pattern)  # tokenize each word
            words.extend(word_list)  # add to words list
            # add to patterns list
            documents.append(((word_list), intent["tag"]))

            if intent["tag"] not in classes:  # add to tags list if not already there
                classes.append(intent["tag"])

    words = [
        lemmatizer.lemmatize(word.lower()) for word in words if word not in ignore_words
    ]  # lemmatize and lower each word
    # remove duplicates and sort
    words = sorted(set(words))
    classes = sorted(set(classes))

    # create training data
    training = []
    output = []
    out_empty = [0] * len(classes)  # empty list for output

    for document in documents:
        bag = []
        word_patterns = document[0]
        word_patterns = [
            lemmatizer.lemmatize(w.lower()) for w in word_patterns
        ]  # lemmatize each word

        for word in words:
            bag.append(1) if word in word_patterns else bag.append(0)
        output_row = list(out_empty)
        output_row[classes.index(document[1])] = 1
        training.append(bag)
        output.append(output_row)

    training = np.array(training)
    output = np.array(output)

    with open("data.pickle", "wb") as f:
        pickle.dump((words, classes, training, output), f)

    # create model (machine learning)
    model = Sequential()
    model.add(
        Dense(256, input_shape=(len(training[0]),), activation="relu")
    )  # input layer
    model.add(Dropout(0.4))  # dropout layer
    model.add(Dense(128, activation="relu"))  # hidden layer
    model.add(Dropout(0.4))  # dropout layer
    model.add(Dense(64, activation="relu"))  # hidden layer
    model.add(Dropout(0.4))  # dropout layer
    model.add(Dense(len(output[0]), activation="softmax"))  # output layer
    adam = Adam(learning_rate=0.001)  # optimizer
    model.compile(
        loss="categorical_crossentropy", optimizer=adam, metrics=["accuracy"]
    )  # compile model
    model.fit(
        training, output, epochs=300, batch_size=10, verbose=1
    )  # fit model (train)
    model.save("chatbot-model.h5")  # save model
    print("Done")


# clean up message
def clean_up_message(message):
    message_word_list = nltk.word_tokenize(message)
    message_word_list = [
        lemmatizer.lemmatize(word.lower()) for word in message_word_list
    ]
    return message_word_list


# bag of words, 0 or 1 for each word in the bag that exists in the message
def bag_of_words(message, words):
    message_word = clean_up_message(message)
    bag = [0] * len(words)
    for w in message_word:
        for i, word in enumerate(words):
            if word == w:
                bag[i] = 1
    return np.array(bag)


# context
context = {}


# predict class, return list of tuples (tag, probability)
def predict_class(message, ERROR_THRESHOLD=0.25):
    bow = bag_of_words(message, words)
    res = model.predict(np.array([bow]))[0]
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append((classes[r[0]], r[1]))
    return return_list

def get_response(message, id="000"):
    spell = Speller()
    corrected_message = spell(message)
    results = predict_class(corrected_message)
    
    if results:
        while results:
            for intent in intents["intents"]:
                if intent["tag"] == results[0][0]:
                    if intent["tag"].lower() == "reiterate":
                        if context:
                            for tg in intents["intents"]:
                                if ("context_set" in tg and tg["context_set"] == context[id]):
                                    return str(random.choice(tg["responses"]))
                        return str(random.choice(intent["responses"]))
                    if "context_set" in intent and intent["context_set"] != "":
                        context[id] = intent["context_set"]
                    return str(random.choice(intent["responses"]))
            results.pop(0)
    
    # Gemini API fallback
    if gemini_model:
        try:
            response = gemini_model.generate_content(
                f"You are a mental health support chatbot. Respond to: {message}\n"
                "Keep response brief (1-2 sentences), empathetic, and mental health focused.\n"
                "For serious concerns, suggest professional help."
            )
            if response and hasattr(response, 'text'):
                return str(response.text)
        except Exception as e:
            print(f"Gemini API Error: {str(e)}")
    
    return "I'm here for you. How can I assist you today?"